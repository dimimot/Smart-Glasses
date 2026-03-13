# Config Variables — Πλήρης Ανάλυση

> Αρχείο: `v2/app/config.py`
> Τελευταία ενημέρωση: 2026-03-11

---

## Κατηγορίες

| Σύμβολο | Σημασία |
|---------|---------|
| ✅ | Χρησιμοποιείται κανονικά |
| ⚠️ | Εσωτερική / intermediate — δεν εξάγεται |
| ❌ | Δεν χρησιμοποιείται πουθενά |
| 🔴 | Πρόβλημα / duplicated definition |

---

## 1. Path Constants

### `APP_ROOT` ⚠️
```python
APP_ROOT = Path(__file__).resolve().parent
```
- **Τι είναι:** Το path του φακέλου `v2/app/`
- **Πού χρησιμοποιείται:** Μόνο εσωτερικά στο `config.py` για να υπολογίσει `V2_ROOT` και `YOLO_WEIGHTS_DIR`
- **Εξάγεται εκτός config:** ❌ Κανένα αρχείο δεν το κάνει import

---

### `V2_ROOT` ⚠️
```python
V2_ROOT = APP_ROOT.parent
```
- **Τι είναι:** Το path του φακέλου `v2/`
- **Πού χρησιμοποιείται:** Μόνο εσωτερικά για να υπολογίσει `PROJECT_ROOT`
- **Εξάγεται εκτός config:** ❌ Κανένα αρχείο δεν το κάνει import

---

### `PROJECT_ROOT` ✅
```python
PROJECT_ROOT = V2_ROOT.parent  # → /Users/.../Smart_Glasses
```
- **Τι είναι:** Το root path ολόκληρου του project
- **Πού χρησιμοποιείται:**
  - `send_pic.py` → βρίσκει images στο `Data/Input_image/`
  - `path_utils.py` → βάση για relative paths στα logs
- **Εξάγεται εκτός config:** ✅

---

### `DATA_DIR` ✅
```python
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "Data"))
```
- **Τι είναι:** Root φάκελος για όλα τα data (εικόνες, prompts, logs, output)
- **Default:** `Smart_Glasses/Data/`
- **Override:** Env variable `DATA_DIR`
- **Πού χρησιμοποιείται:**
  - `describe.py` → system prompts, αποθήκευση περιγραφής
  - `mobile.py` → `received_images/`, `logs/`, `Generated_Text/`
  - `tools.py` → `received_images/`
  - `ssl_cert.py` → `certs/`
- **Εξάγεται εκτός config:** ✅ (4 αρχεία)

---

## 2. YOLO Paths

### `YOLO_WEIGHTS_DIR` ⚠️
```python
YOLO_WEIGHTS_DIR = APP_ROOT / "models" / "weights"
# → v2/app/models/weights/
```
- **Τι είναι:** Φάκελος που περιέχει τα YOLO weights
- **Πού χρησιμοποιείται:** Μόνο εσωτερικά για να υπολογίσει `YOLO_WEIGHTS`
- **Εξάγεται εκτός config:** ❌ Κανένα αρχείο δεν το κάνει import

---

### `YOLO_WEIGHTS` ✅
```python
YOLO_WEIGHTS = Path(os.environ.get("YOLO_WEIGHTS", YOLO_WEIGHTS_DIR / "yolo26n.pt"))
```
- **Τι είναι:** Path προς το αρχείο weights του YOLO μοντέλου
- **Default:** `v2/app/models/weights/yolo26n.pt`
- **Override:** Env variable `YOLO_WEIGHTS`
- **Πού χρησιμοποιείται:**
  - `yolo_model.py` → `load_model()` — φορτώνει το YOLO μοντέλο
  - `check_yolo_classes.py` (script) → εκτυπώνει τα COCO classes
- **Εξάγεται εκτός config:** ✅ (2 αρχεία)

---

## 3. Pipeline & Model Settings

### `PIPELINE_NAME` ❌
```python
PIPELINE_NAME = "describe_loop_return"
```
- **Τι είναι:** Όνομα pipeline (από παλαιότερη αρχιτεκτονική)
- **Πού χρησιμοποιείται:** **ΠΟΥΘΕΝΑ** — ούτε import, ούτε χρήση σε κανένα αρχείο
- **Εξάγεται εκτός config:** ❌
- **Σχόλιο:** Υπόλειμμα από προηγούμενη έκδοση όπου υπήρχαν πολλαπλά named pipelines. Σήμερα υπάρχει μόνο το `describe.py` με τη συνάρτηση `run()`. **Μπορεί να αφαιρεθεί.**

---

### `MODEL` ✅
```python
MODEL = os.environ.get("MODEL", "qwen3_vl")
```
- **Τι είναι:** Επιλογή VLM backend
- **Επιλογές:** `"qwen3_vl"` | `"llava"` | `"blip2"` | `"blip_large"`
- **Default:** `"qwen3_vl"`
- **Override:** Env variable `MODEL`
- **Πού χρησιμοποιείται:**
  - `describe.py` → default parameter του `run()` → `_select_model(model)`
- **Εξάγεται εκτός config:** ✅ (1 αρχείο)

---

### `PREPROC` ✅
```python
PREPROC = os.environ.get("PREPROC", "opencv")
```
- **Τι είναι:** Backend preprocessing εικόνας πριν από το VLM
- **Επιλογές:** `"opencv"` | `"pillow"`
- **Default:** `"opencv"`
- **Override:** Env variable `PREPROC`
- **Πού χρησιμοποιείται:**
  - `describe.py` → default parameter του `run()` → `_read_and_preprocess()`
- **Σημείωση:** Για `qwen3_vl` το preprocessing παρακάμπτεται εντελώς (raw PIL Image)
- **Εξάγεται εκτός config:** ✅ (1 αρχείο)

---

## 4. LM Studio Settings

### `LM_STUDIO_BASE_URL` 🔴
```python
# config.py:
LM_STUDIO_BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:9094")

# qwen3_vl_lmstudio.py (ΞΕΧΩΡΙΣΤΗ ΑΝΑΓΝΩΣΗ):
LM_STUDIO_BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:9094")
```
- **Τι είναι:** URL του LM Studio server (OpenAI-compatible API)
- **Default:** `http://127.0.0.1:9094`
- **Override:** Env variable `LM_STUDIO_BASE_URL`
- **Πού χρησιμοποιείται:**
  - `qwen3_vl_lmstudio.py` → **διαβάζει απευθείας από `os.environ`**, ΔΕΝ κάνει import από config
  - `config.py` → ορίζεται αλλά **κανένας δεν το κάνει import**
- **Πρόβλημα:** **Διπλή ορισμός** — ορίζεται και στο `config.py` και στο `qwen3_vl_lmstudio.py` ανεξάρτητα. Το `config.py` version είναι αχρησιμοποίητο. Η τιμή φτάνει σωστά μόνο μέσω του `.env`.

---

### `LM_STUDIO_MODEL_NAME` 🔴
```python
# config.py:
LM_STUDIO_MODEL_NAME = os.environ.get("LM_STUDIO_MODEL_NAME", "qwen3-vl-32b-instruct")

# qwen3_vl_lmstudio.py (ΞΕΧΩΡΙΣΤΗ ΑΝΑΓΝΩΣΗ):
LM_STUDIO_MODEL_NAME = os.environ.get("LM_STUDIO_MODEL_NAME", "Qwen3-VL-8B-Instruct-MLX-4bit")
#                                                                 ^^^ ΔΙΑΦΟΡΕΤΙΚΟ DEFAULT!
```
- **Τι είναι:** Όνομα μοντέλου όπως φαίνεται στο LM Studio
- **Override:** Env variable `LM_STUDIO_MODEL_NAME`
- **Πού χρησιμοποιείται:**
  - `describe.py` → `from v2.app.config import LM_STUDIO_MODEL_NAME` → χρησιμοποιείται ως `model_id` που επιστρέφεται από `_select_model()` (εμφανίζεται στα logs)
  - `qwen3_vl_lmstudio.py` → ορίζει το **δικό του** `LM_STUDIO_MODEL_NAME` από env και το χρησιμοποιεί στο API call
- **Πρόβλημα:** **Διπλή ορισμός με ΔΙΑΦΟΡΕΤΙΚΑ defaults:**
  - `config.py` default: `"qwen3-vl-32b-instruct"`
  - `qwen3_vl_lmstudio.py` default: `"Qwen3-VL-8B-Instruct-MLX-4bit"`
  - Αν δεν οριστεί στο `.env`, τα δύο θα έχουν διαφορετική τιμή.
  - Η πραγματική τιμή που στέλνεται στο API είναι αυτή του `qwen3_vl_lmstudio.py`.

---

## 5. Feature Toggles

### `TIME_LOGS` ✅
```python
TIME_LOGS = os.environ.get("TIME_LOGS", "ON").strip().upper() == "ON"
```
- **Τι είναι:** Boolean — ενεργοποιεί/απενεργοποιεί την καταγραφή latency σε CSV
- **Default:** `True` (ON)
- **Override:** Env variable `TIME_LOGS=ON` ή `TIME_LOGS=OFF`
- **Πού χρησιμοποιείται:**
  - `mobile.py` → `if TIME_LOGS:` → γράφει σε `Data/logs/timestamps.csv`
- **Εξάγεται εκτός config:** ✅ (1 αρχείο)

---

### `YOLO_ENABLED` ✅
```python
YOLO_ENABLED = os.environ.get("YOLO_ENABLED", "ON").strip().upper() == "ON"
```
- **Τι είναι:** Boolean — ενεργοποιεί/απενεργοποιεί το YOLO pipeline
- **Default:** `True` (ON)
- **Override:** Env variable `YOLO_ENABLED=ON` ή `YOLO_ENABLED=OFF`
- **Πού χρησιμοποιείται:**
  - `describe.py` → `if YOLO_ENABLED:` → τρέχει ή παρακάμπτει το YOLO detection
  - `describe.py` → επιλογή system prompt (`include_yolo_prompt` vs `general_prompt`)
  - `mobile.py` → `yolo_field = ("..." if YOLO_ENABLED else "-")` → στα timestamp logs
- **Εξάγεται εκτός config:** ✅ (2 αρχεία)

---

## Σύνοψη

| Μεταβλητή | Status | Χρησιμοποιείται από |
|-----------|--------|---------------------|
| `APP_ROOT` | ⚠️ Internal | Μόνο εντός config.py |
| `V2_ROOT` | ⚠️ Internal | Μόνο εντός config.py |
| `PROJECT_ROOT` | ✅ | `send_pic.py`, `path_utils.py` |
| `DATA_DIR` | ✅ | `describe.py`, `mobile.py`, `tools.py`, `ssl_cert.py` |
| `YOLO_WEIGHTS_DIR` | ⚠️ Internal | Μόνο εντός config.py |
| `YOLO_WEIGHTS` | ✅ | `yolo_model.py`, `check_yolo_classes.py` |
| `PIPELINE_NAME` | ❌ **Αχρησιμοποίητο** | Πουθενά |
| `MODEL` | ✅ | `describe.py` |
| `PREPROC` | ✅ | `describe.py` |
| `LM_STUDIO_BASE_URL` | 🔴 Duplicate | config version: κανείς — `qwen3_vl_lmstudio.py` διαβάζει απευθείας env |
| `LM_STUDIO_MODEL_NAME` | 🔴 Duplicate + ≠ default | config version: `describe.py` (logs μόνο) — `qwen3_vl_lmstudio.py` διαβάζει απευθείας env με διαφορετικό default |
| `TIME_LOGS` | ✅ | `mobile.py` |
| `YOLO_ENABLED` | ✅ | `describe.py`, `mobile.py` |

---

## Προτεινόμενες Ενέργειες (να γίνουν αργότερα)

### 1. `PIPELINE_NAME` — Αφαίρεση
Δεν χρησιμοποιείται πουθενά. Μπορεί να αφαιρεθεί χωρίς συνέπειες.

### 2. `LM_STUDIO_BASE_URL` / `LM_STUDIO_MODEL_NAME` — Ενοποίηση
Το `qwen3_vl_lmstudio.py` πρέπει να σταματήσει να διαβάζει env απευθείας
και να κάνει import από config:
```python
# Αντί για:
LM_STUDIO_BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "...")

# Να γίνει:
from v2.app.config import LM_STUDIO_BASE_URL, LM_STUDIO_MODEL_NAME
```
Έτσι υπάρχει **μία μόνο πηγή αλήθειας** και εξαφανίζεται το διαφορετικό default.

### 3. `APP_ROOT`, `V2_ROOT`, `YOLO_WEIGHTS_DIR` — ΟΚ ως έχουν
Είναι intermediate helpers εντός config.py. Δεν χρειάζεται να αφαιρεθούν,
αλλά μπορούν να βγουν από το `__all__` αφού δεν εξάγονται.

