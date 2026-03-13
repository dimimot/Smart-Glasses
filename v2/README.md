# VLM Smart Glasses - Python Server

The Python FastAPI backend that receives images and generates descriptions using Vision Language Models.

## 📋 What the Server Does

- 🔌 **REST API** - Receives images and returns descriptions
- 🤖 **Vision Language Models** - Qwen3-VL, BLIP, LLaVA
- 🚦 **YOLO Detection** - Traffic light detection (optional)
- 💾 **State Management** - In-memory storage for captions and status
- 📊 **Performance Logging** - Timing logs for each request
- 🔄 **Long-polling Support** - Real-time updates for clients

## 🚀 Quick Start

### Prerequisites

```bash
# Check Python version
python3.9 --version  # Must be 3.9
```

### Installation

```bash
# 1. Navigate to project root
cd Smart_Glasses

# 2. Create virtual environment
python3.9 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env

# 5. Edit .env with your settings
nano .env

# 6. Start server
python -m v2.app.main
```

Server will start at: **http://localhost:5050**

## ⚙️ Configuration (.env)

```env
# ────────────────────────────────────────────────────────────
# VISION LANGUAGE MODEL SETTINGS
# ────────────────────────────────────────────────────────────

# Model choice: "qwen3_vl" | "blip_large" | "blip2" | "llava"
MODEL=qwen3_vl

# LM Studio Configuration (for Qwen3-VL via local LM Studio)
LM_STUDIO_BASE_URL=http://127.0.0.1:9094
LM_STUDIO_MODEL_NAME=Qwen3-VL-8B-Instruct-MLX-4bit

# Image preprocessing: "opencv" | "pillow"
PREPROC=opencv


# ────────────────────────────────────────────────────────────
# OPTIONAL FEATURES
# ────────────────────────────────────────────────────────────

# Enable YOLO for traffic light detection
YOLO_ENABLED=ON    # ON | OFF

# Enable performance timing logs
TIME_LOGS=ON       # ON | OFF


# ────────────────────────────────────────────────────────────
# PATHS (Optional - defaults to ./Data)
# ────────────────────────────────────────────────────────────

DATA_DIR=./Data
YOLO_WEIGHTS=./v2/app/models/weights/yolo26n.pt
```

## 🔌 API Endpoints

### Health Check
```bash
GET /health
# Response: {"status": "ok"}
```

### Index
```bash
GET /
# Returns: service info, version, description
```

### Upload & Process Image
```bash
POST /mobile/process
Content-Type: multipart/form-data

Parameters:
  - image: <binary file> (required)
  - src: "mobile" | "pi" (optional, default: "mobile")

Response (200):
{
  "description": "..."
}

# Example with curl:
curl -X POST http://localhost:5050/mobile/process \
  -F "image=@photo.jpg" \
  -F "src=mobile"
```

### Get Latest Caption (Immediate)
```bash
GET /mobile/caption_latest
Query Parameters:
  - source: "mobile" | "pi" (default: "pi")
  - since: unix_timestamp (optional)

Response (200):
{
  "caption": "Description text...",
  "created_at": 1234567890,
  "source": "mobile"
}

Response (204): No caption available

# Example:
curl http://localhost:5050/mobile/caption_latest?source=mobile&since=1234567800
```

### Get Next Caption (Long-polling)
```bash
GET /mobile/caption_next
Query Parameters:
  - source: "mobile" | "pi" (default: "pi")
  - since: unix_timestamp (optional)
  - timeout: seconds (default: 25, max: 300)

Response (200): New caption when available
Response (204): Timeout - no new caption

# Example: Wait up to 30 seconds for new caption
curl http://localhost:5050/mobile/caption_next?source=mobile&since=1234567800&timeout=30
```

### Get Pi Status
```bash
GET /api/pi/status

Response (200):
{
  "online": true,
  "last_seen": 1234567890
}

# Pi is considered online if last_seen < 15 seconds ago
```

### Get Pi Status (Long-polling)
```bash
GET /api/pi/status_next
Query Parameters:
  - since: unix_timestamp (optional)
  - timeout: seconds (default: 15, max: 300)

Response (200): New status
Response (204): Timeout - no status change
Response (500): Server error

# Example: Wait for Pi status change
curl http://localhost:5050/api/pi/status_next?since=1234567800&timeout=20
```

## 📁 Project Structure

```
Smart_Glasses/
├── v2/
│   ├── __init__.py
│   │
│   └──  app/                         ← Main application
│       ├── __init__.py
│       ├── main.py                  ← Entry point
│       ├── config.py                ← Environment configuration
│       ├── state.py                 ← In-memory state management
│       │
│       ├── api/                     ← API layer
│       │   ├── __init__.py
│       │   ├── api_router.py        ← Main router
│       │   └── routers/
│       │       ├── core.py          ← /health, /status
│       │       └── mobile.py        ← /mobile/* endpoints
│       │
│       ├── models/                  ← AI Models
│       │   ├── __init__.py
│       │   ├── yolo_model.py        ← YOLO detection
│       │   ├── BLIP/
│       │   ├── BLIP2/
│       │   ├── LLava/
│       │   └── Qwen/
│       │
│       ├── pipelines/               ← Processing pipelines
│       │   ├── __init__.py
│       │   ├── describe.py          ← Image description pipeline
│       │   └── detect.py            ← YOLO detection pipeline
│       │
│       ├── receivers/               ← Server setup
│       │   ├── __init__.py
│       │   └── gateway_server.py    ← FastAPI + Uvicorn setup
│       │
│       └──  utils/                   ← Utilities
│           ├── __init__.py
│           ├── path_utils.py        ← Path helpers
│           ├── image_preprocess.py  ← OpenCV/Pillow preprocessing
│           ├── torch_utils.py       ← PyTorch helpers
│           └── server/
│              ├── ssl_cert.py      ← SSL certificate handling
│              └── cors_web.py      ← CORS configuration
│
├── Data/                            ← All data & artifacts
│   ├── certs/                       ← SSL certificates (if enabled)
│   ├── Generated_Text/              ← Image descriptions (output)
│   ├── logs/                        ← Performance logs (timestamps.csv)
│   ├── Output_image/                ← YOLO debug images
│   ├── received_images/             ← Uploaded images
│   └── system_prompts_qwen/         ← Qwen prompts (general & YOLO-specific)
│
├── requirements.txt                 ← Dependencies
├── .env.example                     ← Configuration template
└── README.md                        ← This file
```

## 🤖 Supported Models

### Qwen3-VL (Recommended)
```env
MODEL=qwen3_vl
LM_STUDIO_BASE_URL=http://127.0.0.1:9094
LM_STUDIO_MODEL_NAME=Qwen3-VL-8B-Instruct-MLX-4bit
```
- **Best quality** descriptions
- Runs via LM Studio locally
- Requires 8GB+ VRAM
- Supports context from YOLO detection

### BLIP Large
```env
MODEL=blip_large
```
- Lighter weight
- Good for low-resource environments
- No context support

### BLIP2
```env
MODEL=blip2
```
- Similar to BLIP Large
- Different architecture

### LLaVA 1.5
```env
MODEL=llava
```
- Good balance of quality & speed

## 🚦 YOLO Detection

Optional traffic light detection pipeline.

### Enable/Disable
```env
YOLO_ENABLED=ON    # Enable YOLO detection
YOLO_ENABLED=OFF   # Disable YOLO detection
```

### How It Works
1. Image arrives at `/mobile/process`
2. If YOLO_ENABLED=ON:
   - Run YOLO detection (detect.py)
   - Extract traffic light states
   - Pass as context to vision model
3. Qwen uses this context in  prompt
4. Final description includes traffic light info

### Output
- **Traffic light state:** RED, GREEN, UNKNOWN
- **Confidence score:** 0.0-1.0
- **Position:** Top, Bottom, Left, Right, Center
- **Debug image:** Saved to `Data/Output_image/yolo_latest.jpg`

## 📊 Performance & Logging

### Timing Logs
When `TIME_LOGS=ON`, a CSV is created at `Data/logs/timestamps.csv`:

```
Time (image received) | Yolo (completed) | Description generated | Total time
2026-03-13T10:30:45.123 | 0.482 | 2.341 | 3.125
2026-03-13T10:31:12.456 | 0.510 | 2.287 | 3.450
```

Columns:
- **Time (image received):** ISO timestamp when request arrived
- **Yolo (completed):** Duration of YOLO detection (seconds), or "-" if disabled
- **Description generated:** Duration of VLM processing (seconds)
- **Total time:** End-to-end latency (seconds)








## State Management

The server maintains in-memory state for real-time updates:

```python
# In v2/app/state.py
latest_by_source = {
    "pi": {"caption": "...", "created_at": 123456, "source": "pi"},
    "mobile": {"caption": "...", "created_at": 123457, "source": "mobile"}
}

last_caption_ts = {"pi": 123456, "mobile": 123457}
last_seen_pi = 123456  # For online status

caption_cond = {  # asyncio.Condition for each source
    "pi": Condition(),
    "mobile": Condition()
}
status_cond = Condition()  # For Pi status changes
```

## Useful Commands

```bash
# Check server health from terminal
curl http://localhost:5050/health

# Test image upload
curl -X POST http://localhost:5050/mobile/process \
  -F "image=@Data/Input_image/test_image.jpg" \
  -F "src=mobile"

# Check Pi status
curl http://localhost:5050/api/pi/status

# Watch logs in real-time
tail -f Data/logs/timestamps.csv


---

**Python:** 3.9
**Framework:** FastAPI + Uvicorn


