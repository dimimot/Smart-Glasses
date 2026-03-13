# VLM Smart Glasses - Flutter Mobile App

The mobile application for iOS/Android that captures photos and sends them to the VLM server to receive image descriptions.

## What It Does

- **Capture photos** from the mobile camera
- **Upload** to the VLM server
- **Get description** of the image
- **Text-to-speech** to read the description aloud

### Prerequisites

- Flutter SDK
- Dart SDK (included in Flutter)
- IDE: IntelliJ IDEA, VS Code, Android Studio

### Setup

```bash
# 1. Open the project
cd flutter_app/tts_cam_test2

# 2. Download dependencies
flutter pub get

# 3. Configure Server URL
# Open lib/main.dart
# Find the SERVER_URL line and change the address
# Example: http://192.168.1.100:5050

# 4. Run on device or emulator
flutter run


## ⚙️ Configure Server Connection

In `lib/main.dart`, set the `SERVER_URL`:

```dart
const String SERVER_URL = 'http://YOUR_SERVER_IP:5050';
```

### Examples:
```dart
// Local development
const String SERVER_URL = 'http://127.0.0.1:5050';

// Network
const String SERVER_URL = 'http://192.168.1.100:5050';

// Remote server
const String SERVER_URL = 'http://example.com:5050';
```

## 📱 Features

### 1. Take Photo from Camera
Tap the button and select or take a photo

### 2. Send to Server
The app automatically uploads the image and Shows an indicator

### 3. Receive Description
Waits for server response and displays the description text

### 4. Text-to-Speech (TTS)
The description is read aloud using text-to-speech.


## Dependencies

- **image_picker** - Select/capture images
- **http** - HTTP requests
- **flutter_tts** - Text-to-speech
- **shared_preferences** - Local storage


