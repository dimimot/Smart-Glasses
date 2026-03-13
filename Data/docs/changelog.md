# Changelog — Τι άλλαξε και γιατί

> Ημερομηνία: 2026-03-11

---

## 1. `v2/app/config.py`

### Αφαιρέθηκε: `PIPELINE_NAME`
```python
# ΑΦΑΙΡΕΘΗΚΕ:
PIPELINE_NAME = "describe_loop_return"
```
**Γιατί:** Δεν χρησιμοποιείται πουθενά στον κώδικα. Υπήρχε μόνο στο `config.py` και στο `__all__` χωρίς κανένα import από άλλο αρχείο. Ήταν υπόλειμμα παλαιότερης αρχιτεκτονίας όπου υπήρχαν πολλαπλά named pipelines.

---

### Διορθώθηκε: `LM_STUDIO_MODEL_NAME` default
```python
# ΠΡΙΝ (λάθος):
LM_STUDIO_MODEL_NAME = os.environ.get("LM_STUDIO_MODEL_NAME", "qwen3-vl-8b-instruct")

# ΜΕΤΑ (σωστό):
LM_STUDIO_MODEL_NAME = os.environ.get("LM_STUDIO_MODEL_NAME", "Qwen3-VL-8B-Instruct-MLX-4bit")
```
**Γιατί:** Το default δεν ταίριαζε με το πραγματικό όνομα του μοντέλου στο LM Studio. Το σωστό όνομα είναι `Qwen3-VL-8B-Instruct-MLX-4bit` (case-sensitive — το LM Studio το απαιτεί ακριβώς έτσι).

---

### Καθαρίστηκε: `__all__`
```python
# ΑΦΑΙΡΕΘΗΚΑΝ από το __all__:
"APP_ROOT"        # εσωτερική intermediate μεταβλητή, δεν εξάγεται
"V2_ROOT"         # εσωτερική intermediate μεταβλητή, δεν εξάγεται
"PIPELINE_NAME"   # αφαιρέθηκε (βλ. παραπάνω)
"YOLO_WEIGHTS_DIR" # εσωτερική intermediate μεταβλητή, δεν εξάγεται
```
**Γιατί:** Το `__all__` πρέπει να περιέχει μόνο ό,τι χρησιμοποιείται εξωτερικά. `APP_ROOT`, `V2_ROOT`, `YOLO_WEIGHTS_DIR` υπάρχουν στο config μόνο για να υπολογίσουν άλλες τιμές — κανένα άλλο αρχείο δεν τις κάνει import.

**Σημείωση:** Οι μεταβλητές (`APP_ROOT`, `V2_ROOT`, `YOLO_WEIGHTS_DIR`) δεν αφαιρέθηκαν από τον κώδικα — μόνο από το `__all__`. Εξακολουθούν να λειτουργούν εσωτερικά.

---

## 2. `v2/app/models/Qwen/qwen3_vl_lmstudio.py`

### Αφαιρέθηκαν: duplicate μεταβλητές
```python
# ΑΦΑΙΡΕΘΗΚΑΝ:
LM_STUDIO_BASE_URL   = os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:9094")
LM_STUDIO_MODEL_NAME = os.environ.get("LM_STUDIO_MODEL_NAME", "Qwen3-VL-8B-Instruct-MLX-4bit")

# ΑΝΤΙΚΑΤΑΣΤAΘΗΚΑΝ ΜΕ:
from v2.app.config import LM_STUDIO_BASE_URL, LM_STUDIO_MODEL_NAME
```
**Γιατί — το πρόβλημα:** Το αρχείο διάβαζε τις ίδιες env variables ανεξάρτητα από το `config.py`, δημιουργώντας **δύο ορισμούς** της ίδιας τιμής. Αν κάποιος άλλαζε το default στο config, το `qwen3_vl_lmstudio.py` δεν θα το έβλεπε. Επιπλέον το παλιό default ήταν διαφορετικό από αυτό του config, που σημαίνει ότι χωρίς `.env` τα δύο είχαν **διαφορετική τιμή**.

**Αποτέλεσμα:** Πλέον υπάρχει **μία μόνο πηγή αλήθειας** για αυτές τις τιμές — το `config.py`.

**Πού χρησιμοποιούνται στο αρχείο:**
- `LM_STUDIO_BASE_URL` → στη `_post_chat_completions()` ως base URL για το HTTP request
- `LM_STUDIO_MODEL_NAME` → στο payload της `generate_caption()` ως `"model": LM_STUDIO_MODEL_NAME`

---

## 3. `.env` και `.env.example`

### Διορθώθηκε: `LM_STUDIO_MODEL_NAME`
```env
# ΠΡΙΝ:
LM_STUDIO_MODEL_NAME=qwen3-vl-32b-instruct

# ΜΕΤΑ:
LM_STUDIO_MODEL_NAME=Qwen3-VL-8B-Instruct-MLX-4bit
```
**Γιατί:** Το `.env` είχε το λάθος (παλιό) όνομα μοντέλου. Ενημερώθηκε ώστε να ταιριάζει με το πραγματικό μοντέλο που τρέχει στο LM Studio.

---

## 4. Missing `__init__.py` files — Προστέθηκαν

| Αρχείο | Κατάσταση πριν |
|--------|----------------|
| `v2/app/pipelines/__init__.py` | ❌ Έλειπε |
| `v2/app/receivers/__init__.py` | ❌ Έλειπε |
| `v2/app/utils/__init__.py` | ❌ Έλειπε |
| `v2/app/utils/server/__init__.py` | ❌ Έλειπε |

**Γιατί:** Αυτοί οι φάκελοι χρησιμοποιούνται ως Python packages (γίνονται imports από άλλα αρχεία), αλλά δεν είχαν `__init__.py`. Χωρίς αυτό, σε ορισμένες περιπτώσεις τα imports μπορεί να αποτύχουν. Δείτε το αρχείο `packages_guide.md` για αναλυτική εξήγηση.

---

## Σύνοψη

| Αρχείο | Τι άλλαξε |
|--------|-----------|
| `config.py` | Αφαίρεση `PIPELINE_NAME`, fix model name default, καθαρισμός `__all__` |
| `qwen3_vl_lmstudio.py` | Αφαίρεση duplicate env reads, import από config |
| `.env` | Fix model name |
| `.env.example` | Fix model name |
| `v2/app/pipelines/__init__.py` | Νέο (κενό) |
| `v2/app/receivers/__init__.py` | Νέο (κενό) |
| `v2/app/utils/__init__.py` | Νέο (κενό) |
| `v2/app/utils/server/__init__.py` | Νέο (κενό) |

