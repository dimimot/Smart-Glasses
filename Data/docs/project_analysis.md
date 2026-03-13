# 🔍 Ανάλυση Project Smart_Glasses

## 🎯 Τι είναι το project

Ένα σύστημα υποβοήθησης **τυφλών/αμβλυώπων χρηστών** στο αστικό περιβάλλον.
Βασική λειτουργία: ο χρήστης (ή το Raspberry Pi) τραβά φωτογραφία, το σύστημα αναλύει την εικόνα (φανάρι, πεζοδρόμιο, κίνδυνοι) και επιστρέφει **περιγραφή σε κείμενο** (ή/και TTS στο κινητό).

---

## 🏗️ Αρχιτεκτονική

```
[ Flutter App (κινητό) ]  ←→  [ FastAPI Server (port 5050) ]  ←→  [ AI Models ]
                                         ↑
                          [ Raspberry Pi (src=pi) ]
```

---

## 📦 Κύρια Components

### 1. 🐍 FastAPI Backend — `v2/app/`

Ο κεντρικός server. Τρέχει στο **port 5050** μέσω HTTPS (SSL).

| Αρχείο | Ρόλος |
|--------|-------|
| `main.py` | Εκκίνηση app, register routers, ξεκινά gateway server |
| `config.py` | Όλες οι ρυθμίσεις (paths, YOLO ON/OFF, επιλογή μοντέλου, LM Studio URL) |
| `state.py` | In-memory state: τελευταία caption, Pi status, asyncio Conditions για long-polling |
| `receivers/gateway_server.py` | Δευτερεύων server που δέχεται heartbeats από Raspberry Pi |

**Ενεργά API Endpoints:**

| Route | Τι κάνει |
|-------|----------|
| `POST /mobile/process` | Δέχεται εικόνα (`?src=mobile` ή `?src=pi`), τρέχει YOLO + VLM, επιστρέφει περιγραφή |
| `GET /mobile/caption_latest` | Επιστρέφει αμέσως την τελευταία caption (per source) |
| `GET /mobile/caption_next` | **Long-polling**: περιμένει νέα caption (έως N δευτερόλεπτα) |
| `GET /api/pi/status` | Status Raspberry Pi (online/offline βάσει last_seen) |
| `GET /api/pi/status_next` | Long-polling για Pi status |
| `GET /health` | Health check |

---

### 2. 🤖 AI Pipeline — `v2/app/pipelines/`

**Ροή επεξεργασίας εικόνας:**

```
Εικόνα → [image_preprocess] → [YOLO detect*] → [VLM describe] → Caption
                                  *αν YOLO_ENABLED=ON
```

**`detect.py`** (YOLO Pipeline) — *Προαιρετικό*:
- Ενεργοποιείται/απενεργοποιείται με `YOLO_ENABLED` στο `config.py` (ή env variable)
- Τρέχει YOLOv8/v11 τοπικά
- Ανιχνεύει: φανάρια (κόκκινο/πράσινο), πεζούς, οχήματα
- Αποτελέσματα ενσωματώνονται στο prompt πριν σταλεί στο VLM

**`describe.py`** (VLM Pipeline):
- Φορτώνει prompt από αρχείο (`Data/system_prompts_qwen/`)
- Αν `YOLO_ENABLED=ON`: χρησιμοποιεί `include_yolo_prompt` (με YOLO context)
- Αν `YOLO_ENABLED=OFF`: χρησιμοποιεί `general_prompt` (μόνο VLM)
- Στέλνει εικόνα + prompt στο επιλεγμένο VLM → παίρνει περιγραφή

---

### 3. 🧠 AI Models — `v2/app/models/`

Το μοντέλο επιλέγεται μέσω `MODEL` στο `config.py`:

```python
# Επιλογές: "qwen3_vl" | "llava" | "blip2" | "blip_large"
MODEL = "qwen3_vl"   # ← Βασικό μοντέλο
```

| Model | Περιγραφή | Status |
|-------|-----------|--------|
| **Qwen3-VL** (`Qwen/qwen3_vl_lmstudio.py`) | Vision Language Model — τρέχει **τοπικά μέσω LM Studio** (OpenAI-compatible API, port 9094). Είναι το **κύριο μοντέλο** | ✅ Ενεργό |
| **LLaVA** (`LLava/`) | Εναλλακτικό VLM | 🔄 Διαθέσιμο |
| **BLIP2 / BLIP Large** (`BLIP2/`, `BLIP/`) | Παλαιότερα μοντέλα (από v1) | 🔄 Διαθέσιμο |
| **YOLO** (`yolo_model.py`) | Object detection — YOLOv8/v11 weights τοπικά | ⚙️ Προαιρετικό |

**LM Studio settings (config.py):**
```python
LM_STUDIO_BASE_URL   = "http://127.0.0.1:9094"      # OpenAI-compatible endpoint
LM_STUDIO_MODEL_NAME = "qwen3-vl-32b-instruct"
```

---

### 4. 📱 Flutter App — `v2/flutter_app/main.dart`

Η mobile εφαρμογή. Κάνει:
1. **Τραβάει φωτογραφία** (κάμερα κινητού)
2. **Στέλνει** στο `POST /mobile/process?src=mobile` (multipart)
3. **Long-polling** στο `/mobile/caption_next?source=mobile` — περιμένει αποτέλεσμα
4. **Εμφανίζει** την περιγραφή (και πιθανώς TTS)
5. Παρακολουθεί **status Raspberry Pi** μέσω `/api/pi/status_next`

---

### 5. 🍓 Raspberry Pi

- Λειτουργεί ως **φορητή κάμερα** (γυαλιά / wearable device)
- Τραβάει εικόνες και τις στέλνει στο `POST /mobile/process?src=pi`
- Ο server αναγνωρίζει την πηγή `src=pi` και:
  - Ενημερώνει το `state.last_seen_pi` (heartbeat)
  - Αποθηκεύει caption ξεχωριστά (`state.latest_by_source["pi"]`)
  - Ξυπνά τους long-pollers του Pi status
- Η Flutter app βλέπει αν το Pi είναι online και ενημερώνει τον χρήστη

---

## ⚙️ Βασικές Ρυθμίσεις (`config.py`)

| Μεταβλητή | Default | Περιγραφή |
|-----------|---------|-----------|
| `MODEL` | `"qwen3_vl"` | Επιλογή VLM backend |
| `YOLO_ENABLED` | `ON` | Ενεργοποίηση/απενεργοποίηση YOLO (env: `YOLO_ENABLED`) |
| `TIME_LOGS` | `ON` | Logging χρόνων latency σε CSV (env: `TIME_LOGS`) |
| `LM_STUDIO_BASE_URL` | `http://127.0.0.1:9094` | LM Studio endpoint |
| `LM_STUDIO_MODEL_NAME` | `qwen3-vl-32b-instruct` | Όνομα μοντέλου στο LM Studio |
| `PREPROC` | `"opencv"` | Backend preprocessing (`"opencv"` ή `"pillow"`) |

---

## 🔄 Πλήρης Ροή Δεδομένων

```
1. Χρήστης πατά κουμπί στο Flutter  (ή το Pi τραβά αυτόματα)
2. Εικόνα POST → /mobile/process?src=mobile|pi
3. Server αποθηκεύει → received_images/current_image.jpg
4. [Αν YOLO_ENABLED=ON] YOLO → ανιχνεύει φανάρια/πεζούς
5. Qwen3-VL (LM Studio) → "Βλέπω πράσινο φανάρι, ο δρόμος φαίνεται ελεύθερος..."
6. State ενημερώνεται, asyncio Condition ξυπνά long-pollers
7. Flutter (που κάνει polling) λαμβάνει caption → εμφανίζει / TTS
```

---

## 📁 Σημαντικά Αρχεία & Φάκελοι

| Path | Ρόλος |
|------|-------|
| `Data/system_prompts_qwen/general_prompt` | Prompt για VLM-only λειτουργία |
| `Data/system_prompts_qwen/include_yolo_prompt` | Prompt που ενσωματώνει YOLO αποτελέσματα |
| `Data/Generated_Text/captions.json` | Ιστορικό τελευταίων 3 captions |
| `Data/Generated_Text/image_description.txt` | Τελευταία περιγραφή (write-through) |
| `Data/logs/timestamps.csv` | Latency logs (χρόνοι YOLO + VLM + total) |
| `Data/received_images/current_image.jpg` | Τρέχουσα εικόνα (αντικαθίσταται κάθε φορά) |
| `v2/scripts/send_pic.py` | Utility για test αποστολή εικόνας |
| `v2/app/utils/image_preprocess.py` | Preprocessing εικόνας (denoise, upscale, CLAHE) |
| `v2/app/utils/ssl_cert.py` | SSL setup για HTTPS |
| `v2/app/models/weights/` | YOLO weights (yolo26n.pt) |

---

## 🗺️ Σύνοψη

> Το project είναι ένα **real-time assistive vision system** για τυφλούς χρήστες.
> Μια φορητή κάμερα (Raspberry Pi `src=pi` ή κινητό `src=mobile`) στέλνει εικόνες σε ένα FastAPI server,
> το οποίο τρέχει προαιρετικά YOLO για object detection και **Qwen3-VL** (μέσω LM Studio) για natural language περιγραφή.
> Η Flutter app λαμβάνει την περιγραφή μέσω long-polling και την παρουσιάζει στον χρήστη.

