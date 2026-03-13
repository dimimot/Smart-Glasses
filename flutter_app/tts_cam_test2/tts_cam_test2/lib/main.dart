import 'dart:typed_data';
import 'dart:async';
import 'dart:convert';
import 'dart:io' show Platform;
import 'dart:ui';                          // για decodeImageFromList
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart'; // για debugPrint
import 'package:flutter_tts/flutter_tts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Glasses App',
      theme: ThemeData(
        brightness: Brightness.dark,
        primarySwatch: Colors.indigo,
        fontFamily: 'Roboto',
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final FlutterTts flutterTts = FlutterTts();
  final ImagePicker picker = ImagePicker();
  String? description;
  String statusMessage = 'Checking smart glasses status...';
  bool _piOnline = false;
  int _lastCaptionTs = 0;   // ενημερώνεται από created_at όταν λαμβάνουμε caption
  int _lastSeen = 0;        // ενημερώνεται από status_next όταν γίνει online
  bool _stopLongPoll = false;   // cancellation flag για loops (dispose)
  bool _captionLoopRunning = false; // προστασία διπλού ξεκινήματος
  bool _isSpeaking = false;   // διατήρησε το stop-before-speak behavior
  String? _lastSpokenCaption;         // το κείμενο της τελευταίας εκφωνηθείσας περιγραφής
  bool _nothingChangedSpoken = false;  // true αφού έχουμε πει "Nothing has changed" μία φορά
  // Watchdog για άμεσο γύρισμα σε offline χωρίς να περιμένουμε το τέλος του long‑poll
  Timer? _offlineWatchdog;

  // Ρύθμιση ταχύτητας TTS (0.0–1.0)
  double _ttsRate = 0.55;

  // Get server URL based on platform
  String get serverUrl {
    return '${baseUrl}/mobile/process';
  }

  // Base URL and endpoint helpers
  String get baseUrl {
    // Emulators
    if (Platform.isAndroid) return 'http://10.0.2.2:5050';
    if (Platform.isIOS) return 'http://localhost:5050';
    // Real device (adjust to your LAN server IP if needed)
    return 'http://172.20.10.3:5050';
  }

  Uri statusNextUri(int since) => Uri.parse('$baseUrl/api/pi/status_next?since=$since&timeout=17');
  Uri captionNextUri(int since, {String source = 'pi'}) =>
      Uri.parse('$baseUrl/mobile/caption_next?source=$source&since=$since&timeout=25');

  // Προαιρετικά (μόνο για χειροκίνητα debug, ΟΧΙ χρήση από την app):
  Uri statusUri() => Uri.parse('$baseUrl/api/pi/status');
  Uri captionLatestUri(int since, {String source = 'pi'}) =>
      Uri.parse('$baseUrl/mobile/caption_latest?source=$source&since=$since');

  Future<void> pickImageAndSend(ImageSource source) async {
    try {
      final XFile? photo = await picker.pickImage(
        source: source,

        // === RESIZE SETTINGS ===
        // Ενεργοποίησε ΕΝΑ από τα παρακάτω κάνοντας uncomment.
        // Για χωρίς resize (original resolution): κάνε comment ΟΛΑ.

        // ΜΕΓΑΛΟ resize (1280×1024):
        //maxWidth: 1280, maxHeight: 1024, imageQuality: 85,

        // ΜΕΣΑΙΟ resize (800×640):
        //maxWidth: 800, maxHeight: 640, imageQuality: 85,

        // ΜΙΚΡΟ resize (640×480):
        maxWidth: 640, maxHeight: 480, imageQuality: 75,

        // ΧΩΡΙΣ RESIZE (original resolution):
        // Κάνε comment ΟΛΑ τα παραπάνω maxWidth/maxHeight/imageQuality
      );

      if (photo != null) {
        setState(() {
          statusMessage = 'Sending image...';
        });

        Uint8List imageBytes = await photo.readAsBytes();
        final imageSizeKB = (imageBytes.lengthInBytes / 1024).toStringAsFixed(1);

        // Εκτύπωση πραγματικής ανάλυσης της εικόνας που θα σταλεί:
        // Χωρίς resize: εκτυπώνει την αρχική ανάλυση (iOS/Android original)
        // Με resize: εκτυπώνει την ανάλυση μετά το resize
        final decodedImage = await decodeImageFromList(imageBytes);
        final imgWidth = decodedImage.width;
        final imgHeight = decodedImage.height;

        final uploadStart = DateTime.now();
        final uploadStartStr = uploadStart.toIso8601String();

        var request = http.MultipartRequest(
          'POST',
          Uri.parse(serverUrl),
        );

        request.files.add(http.MultipartFile.fromBytes(
          'image',
          imageBytes,
          filename: 'photo.jpg',
          contentType: MediaType('image', 'jpeg'),
        ));

        var response = await request.send();
        final endToEndMs = DateTime.now().difference(uploadStart).inMilliseconds;

        debugPrint('=== IMAGE METRICS ===');
        debugPrint('Flutter send time  : $uploadStartStr');
        debugPrint('Platform           : ${Platform.isAndroid ? "Android" : "iOS"}');
        debugPrint('Resolution         : ${imgWidth}x${imgHeight} px');
        debugPrint('Image size         : ${imageSizeKB} KB');
        debugPrint('End-to-end latency : ${endToEndMs} ms  (upload + inference + network)');
        debugPrint('=====================');

        if (response.statusCode == 200) {
          final respStr = await response.stream.bytesToString();
          final desc = _extractDescriptionFromResponseBody(respStr);
          setState(() {
            description = desc;
            statusMessage = 'Image sent successfully!';
          });
          await _speak(desc);
        } else {
          setState(() {
            statusMessage = 'Server error: ${response.statusCode}';
          });
        }
      } else {
        setState(() {
          statusMessage = 'No photo selected.';
        });
      }
    } catch (e) {
      setState(() {
        statusMessage = 'Error: $e';
      });
    }
  }

  // Μόνιμο status long‑poll loop (χωρίς periodic timers και χωρίς fallback GET)
  Future<void> _statusLongPollLoop() async {
    while (mounted && !_stopLongPoll) {
      try {
        final resp = await http
            .get(statusNextUri(_lastSeen))
            .timeout(const Duration(seconds: 20));
        if (!mounted) break;
        if (resp.statusCode == 200) {
          final m = jsonDecode(resp.body) as Map<String, dynamic>;
          final online = (m['online'] == true);
          final lastSeen = (m['last_seen'] ?? 0) as int;
          setState(() {
            _piOnline = online;
            _lastSeen = lastSeen;
            // Καθάρισε το προσωρινό statusMessage από την πράσινη περιοχή.
            // Το μήνυμα για disconnected θα εμφανίζεται χαμηλά, δίπλα στα buttons.
            statusMessage = '';
          });
          if (online) {
            _startCaptionLongPoll();
            _startOfflineWatchdog();
            // Βεβαιώσου ότι στο Android τρέχει Foreground Service για background λειτουργία
            _ensureAndroidFgServiceStarted();
          }
        } else if (resp.statusCode == 204) {
          // Καμία νέα ένδειξη μέσα στο timeout=17 → εκτίμηση κατάστασης με threshold 15s
          final nowSec = DateTime.now().millisecondsSinceEpoch ~/ 1000;
          final onlineNow = (nowSec - _lastSeen) <= 15;
          if (_piOnline != onlineNow) {
            setState(() {
              _piOnline = onlineNow;
              // Μην εμφανίζεις το disconnected μήνυμα στην πράσινη περιοχή.
              // Θα εμφανιστεί χαμηλά στο UI (κάτω από το status section).
              statusMessage = '';
            });
            if (!onlineNow) {
              _stopCaptionLongPoll();
              _stopOfflineWatchdog();
              _ensureAndroidFgServiceStopped();
            }
          }
          // BACKOFF μικρή καθυστέρηση για να αποφύγουμε tight loop σε συνεχόμενα 204
          await Future.delayed(const Duration(milliseconds: 150));
          // Αν παραμείναμε online, σιγουρέψου ότι τρέχει ο watchdog
          if (onlineNow) _startOfflineWatchdog();
        } else if (resp.statusCode >= 500) {
          // Σφάλμα server: εμφάνισε μήνυμα και κάνε μικρό backoff χωρίς αλλαγή online state
          setState(() {
            statusMessage = 'Server error: ${resp.statusCode}';
          });
          await Future.delayed(const Duration(milliseconds: 400));
        }
      } catch (_) {
        // Σφάλμα δικτύου: μικρή παύση, και συνέχισε στο επόμενο long‑poll
        await Future.delayed(const Duration(milliseconds: 300));
      }
      // ΑΜΕΣΩΣ νέο long‑poll
    }
  }

  // Caption long‑poll loop (τρέχει μόνο όταν _piOnline == true)
  void _startCaptionLongPoll() {
    if (_captionLoopRunning) return;
    _captionLoopRunning = true;
    _captionLongPollLoop();
  }

  void _stopCaptionLongPoll() {
    _captionLoopRunning = false; // θα σταματήσει στο επόμενο check
  }

  Future<void> _captionLongPollLoop() async {
    while (mounted && _captionLoopRunning && _piOnline) {
      try {
        final resp = await http
            .get(captionNextUri(_lastCaptionTs, source: 'pi'))
            .timeout(const Duration(seconds: 35));
        if (!_captionLoopRunning || !mounted) break;
        if (resp.statusCode == 200) {
          final m = jsonDecode(resp.body) as Map<String, dynamic>;
          final caption = (m['caption'] ?? '').toString();
          final createdAt = (m['created_at'] ?? 0) as int;
          if (caption.isNotEmpty && createdAt > _lastCaptionTs) {
            setState(() {
              _lastCaptionTs = createdAt;
            });
            const double similarityThreshold = 0.85;
            final sim = _stringSimilarity(caption.trim(), (_lastSpokenCaption ?? '').trim());
            if (sim >= similarityThreshold) {
              // Ίδιο περιεχόμενο με την τελευταία εκφώνηση
              if (!_nothingChangedSpoken) {
                // Πρώτη φορά → εμφάνισε και εκφώνησε "Nothing has changed"
                setState(() {
                  description = 'Nothing has changed. Waiting for a change in the scene.';
                  statusMessage = 'Scene unchanged';
                });
                await _speak('Nothing has changed. Waiting for a change in the scene.');
                _nothingChangedSpoken = true;
              }
              // Επόμενες φορές → σιωπή (κάνε τίποτα)
            } else {
              // Νέο περιεχόμενο → ενημέρωσε και εκφώνησε κανονικά
              _lastSpokenCaption = caption;
              _nothingChangedSpoken = false;
              setState(() {
                description = caption;
                statusMessage = 'New caption received';
              });
              await _speak(caption);
            }
          }
        } else if (resp.statusCode == 204) {
          // BACKOFF μικρή καθυστέρηση για να αποφύγουμε tight loop σε συνεχόμενα 204
          await Future.delayed(const Duration(milliseconds: 150));
        } else if (resp.statusCode >= 500) {
          setState(() {
            statusMessage = 'Caption error: ${resp.statusCode}';
          });
          await Future.delayed(const Duration(milliseconds: 400));
        }
      } catch (_) {
        // δικτυακό/timeout σφάλμα → μικρή αναμονή για να αποφύγουμε tight loop
        await Future.delayed(const Duration(milliseconds: 200));
      }
    }
  }

  // Ξεκινά περιοδικό έλεγχο (ανά 1s) για να εντοπίζει άμεσα όταν έχει περάσει
  // το όριο των 15s από την τελευταία «ένδειξη ζωής» (last_seen ή/και last_caption).
  void _startOfflineWatchdog() {
    if (_offlineWatchdog != null) return; // ήδη τρέχει
    _offlineWatchdog = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!_piOnline) return; // ενδιαφέρει μόνο αν είμαστε online
      final nowSec = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      // Συνυπολόγισε και το τελευταίο caption ως activity, αν υπάρχει
      final lastActive = (_lastSeen > _lastCaptionTs) ? _lastSeen : _lastCaptionTs;
      if (lastActive == 0) return;
      final offline = (nowSec - lastActive) > 15;
      if (offline) {
        if (!mounted) return;
        setState(() {
          _piOnline = false;
          // statusMessage μένει κενό εδώ — το UI δείχνει κάτω το «disconnected» κείμενο
        });
        _stopCaptionLongPoll();
        _stopOfflineWatchdog();
      }
    });
  }

  void _stopOfflineWatchdog() {
    _offlineWatchdog?.cancel();
    _offlineWatchdog = null;
  }

  // -------- Foreground Service (Android) helpers --------
  Future<void> _initForegroundTask() async {
    if (!Platform.isAndroid) return;
    // Ρύθμιση καναλιού ειδοποίησης και επιλογών service
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: 'smart_glasses_bg',
        channelName: 'Background Service',
        channelDescription: 'Keeps Smart Glasses running in background',
        channelImportance: NotificationChannelImportance.DEFAULT,
        priority: NotificationPriority.DEFAULT,
      ),
      iosNotificationOptions: const IOSNotificationOptions(
        showNotification: false,
        playSound: false,
      ),
      foregroundTaskOptions: const ForegroundTaskOptions(
        isOnceEvent: false,
        autoRunOnBoot: false,
        allowWakeLock: true,
        allowWifiLock: true,
      ),
    );
    // Android 13+: ζήτα άδεια ειδοποιήσεων (αν δεν έχει δοθεί)
    await FlutterForegroundTask.requestNotificationPermission();
  }

  Future<void> _ensureAndroidFgServiceStarted() async {
    if (!Platform.isAndroid) return;
    final isRunning = await FlutterForegroundTask.isRunningService;
    if (!isRunning) {
      await FlutterForegroundTask.startService(
        notificationTitle: 'Smart Glasses',
        notificationText: 'Running in background…',
      );
    }
  }

  Future<void> _ensureAndroidFgServiceStopped() async {
    if (!Platform.isAndroid) return;
    final isRunning = await FlutterForegroundTask.isRunningService;
    if (isRunning) {
      await FlutterForegroundTask.stopService();
    }
  }

  String _extractDescriptionFromResponseBody(String respStr) {
    try {
      final obj = jsonDecode(respStr);
      if (obj is Map<String, dynamic>) {
        final d = obj['description'];
        if (d is String) return d;
        if (d is Map<String, dynamic>) {
          return (d['description'] ?? d['caption'] ?? '').toString();
        }
      }
    } catch (_) {}
    return respStr; // fallback
  }

  /// Υπολογίζει ομοιότητα Levenshtein μεταξύ δύο strings.
  /// Επιστρέφει 0.0 (εντελώς διαφορετικά) έως 1.0 (ίδια).
  /// Δεν χρειάζεται εξωτερικό package.
  double _stringSimilarity(String a, String b) {
    if (a == b) return 1.0;
    if (a.isEmpty || b.isEmpty) return 0.0;
    final int lenA = a.length;
    final int lenB = b.length;
    final List<List<int>> dp =
    List.generate(lenA + 1, (i) => List.generate(lenB + 1, (j) => 0));
    for (int i = 0; i <= lenA; i++) dp[i][0] = i;
    for (int j = 0; j <= lenB; j++) dp[0][j] = j;
    for (int i = 1; i <= lenA; i++) {
      for (int j = 1; j <= lenB; j++) {
        if (a[i - 1] == b[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1];
        } else {
          dp[i][j] = 1 +
              [dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]]
                  .reduce((x, y) => x < y ? x : y);
        }
      }
    }
    final int maxLen = lenA > lenB ? lenA : lenB;
    return 1.0 - (dp[lenA][lenB] / maxLen);
  }

  Future<void> _speak(String text) async {
    if (text.trim().isEmpty) return;
    _isSpeaking = true;
    try {
      await flutterTts.setLanguage('en-US');
      // Εφάρμοσε την ταχύτητα ομιλίας πριν την εκφώνηση
      await flutterTts.setSpeechRate(_ttsRate);
      await flutterTts.speak(text);
    } finally {
      _isSpeaking = false;
    }
  }

  @override
  void initState() {
    super.initState();
    _initForegroundTask();
    _stopLongPoll = false;
    _statusLongPollLoop();
    // Ρύθμιση ώστε το speak() να «ολοκληρώνεται» όταν τελειώνει η εκφώνηση
    // για σειριακή αναπαραγωγή χωρίς βίαιο stop/start (iOS & Android)
    () async {
      try {
        await flutterTts.awaitSpeakCompletion(true);

        // iOS: Σταθεροποίηση audio session (χωρίς warm-up)
        if (Platform.isIOS) {
          await flutterTts.setIosAudioCategory(
            IosTextToSpeechAudioCategory.playback,
            [
              IosTextToSpeechAudioCategoryOptions.defaultToSpeaker,
              IosTextToSpeechAudioCategoryOptions.allowBluetooth,
            ],
          );

          // Εφάρμοσε ίδιες ρυθμίσεις με αυτές που θα χρησιμοποιούνται στα speaks
          await flutterTts.setLanguage('en-US');
          await flutterTts.setSpeechRate(_ttsRate);
        }
      } catch (_) {}
    }();
    // Αν ξεκινήσουμε ήδη online (σπάνιο), βεβαιώσου ότι ο watchdog είναι έτοιμος.
    if (_piOnline) _startOfflineWatchdog();
  }

  @override
  void dispose() {
    _stopLongPoll = true; // σταματά τα loops στο επόμενο βήμα
    _captionLoopRunning = false;
    _stopOfflineWatchdog();
    if (Platform.isAndroid) {
      // Σταμάτα το Foreground Service όταν τερματίζεται το widget/app
      FlutterForegroundTask.stopService();
    }
    try {
      flutterTts.stop();
    } catch (_) {}
    super.dispose();
  }

  Future<void> showImageSourceDialog() async {
    await showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Select Image Source'),
          content: const Text('Choose where to get the image from:'),
          actions: [
            TextButton.icon(
              icon: const Icon(Icons.camera_alt),
              label: const Text('Camera'),
              onPressed: () {
                Navigator.pop(context);
                pickImageAndSend(ImageSource.camera);
              },
            ),
            TextButton.icon(
              icon: const Icon(Icons.photo_library),
              label: const Text('Photo Library'),
              onPressed: () {
                Navigator.pop(context);
                pickImageAndSend(ImageSource.gallery);
              },
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Smart Glasses App'),
        centerTitle: true,
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                'Take a photo or select from gallery to get a scene description.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 18),
              ),
              const SizedBox(height: 32),
              if (description != null) ...[
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.indigo.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    children: [
                      const Text(
                        'Description:',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        description!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 16),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
              ],
              const Icon(Icons.volume_up, size: 64, color: Colors.indigo),
              const SizedBox(height: 16),
              Text(
                statusMessage,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 16,
                  color: statusMessage.contains('Error') || statusMessage.contains('error')
                      ? Colors.red
                      : Colors.green,
                ),
              ),
              const SizedBox(height: 32),
              if (_piOnline) ...[
                const SizedBox(height: 12),
                const Text(
                  'Smart glasses are on. Streaming is on. Waiting for description...',
                  textAlign: TextAlign.center,
                ),
              ] else ...[
                const SizedBox(height: 12),
                const Text(
                  'Smart glasses are disconnected. Click "Photo" to take a pic or Turn on smart glasses for streaming mode',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton.icon(
                      onPressed: () => pickImageAndSend(ImageSource.camera),
                      icon: const Icon(Icons.camera_alt),
                      label: const Text('Camera'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                      ),
                    ),
                    const SizedBox(width: 16),
                    ElevatedButton.icon(
                      onPressed: () => pickImageAndSend(ImageSource.gallery),
                      icon: const Icon(Icons.photo_library),
                      label: const Text('Gallery'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 16),
              const Text(
                'For the Simulator: Use Gallery\nFor Real Device: Use Camera',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
        ),
      ),
    );
  }
}