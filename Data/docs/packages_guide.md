# Python Packages — Τι είναι το `__init__.py` και πώς λειτουργεί

---

## Τι είναι ένα Python Package

Στην Python, ένας **φάκελος** γίνεται **package** (ενότητα κώδικα με όνομα) όταν περιέχει ένα αρχείο `__init__.py`.

```
my_folder/          ← απλός φάκελος (δεν μπορείς να κάνεις import)
my_folder/
└── __init__.py     ← package (μπορείς να κάνεις import)
```

Χωρίς `__init__.py` ο Python δεν "βλέπει" τον φάκελο ως ενότητα κώδικα στην Python 2. Στην Python 3.3+ υπάρχουν "namespace packages" που λειτουργούν χωρίς αυτό, αλλά η **best practice** είναι πάντα να το βάζεις για σαφήνεια και συμβατότητα με εργαλεία (linters, IDEs, test runners).

---

## Γιατί το χρειαζόμαστε στο project

Για να γράψεις:
```python
from v2.app.pipelines.describe import run
```

Η Python πρέπει να διαβάσει τον import βήμα-βήμα:
```
v2/          → πρέπει να είναι package → χρειάζεται __init__.py ✅
v2/app/      → πρέπει να είναι package → χρειάζεται __init__.py ✅
v2/app/pipelines/ → πρέπει να είναι package → χρειάζεται __init__.py ✅ (νέο)
describe.py  → το αρχείο
```

Αν **οποιοδήποτε** επίπεδο λείπει το `__init__.py`, το import μπορεί να αποτύχει.

---

## Τι μπαίνει μέσα στο `__init__.py`

### Επιλογή 1: Κενό αρχείο (το πιο συνηθισμένο)
```python
# __init__.py
(κενό)
```
Απλώς δηλώνει ότι "αυτός ο φάκελος είναι package". Τίποτα άλλο.

### Επιλογή 2: Re-exports για βολικά imports
```python
# v2/app/pipelines/__init__.py
from v2.app.pipelines.describe import run as describe
from v2.app.pipelines.detect import run as detect
```
Έτσι μπορείς να γράφεις:
```python
from v2.app.pipelines import describe  # αντί για from v2.app.pipelines.describe import run
```

### Επιλογή 3: Metadata
```python
# __init__.py
__version__ = "2.0.0"
__author__ = "George"
```

**Στο project μας:** Όλα τα `__init__.py` είναι **κενά** — αυτό είναι σωστό και αρκετό.

---

## Χάρτης του project — ποιοι φάκελοι είναι packages

```
Smart_Glasses/
├── v2/                          ✅ package  (__init__.py)
│   ├── app/                     ✅ package  (__init__.py)
│   │   ├── api/                 ✅ package  (__init__.py)
│   │   │   └── routers/         ✅ package  (__init__.py)
│   │   ├── models/              ✅ package  (__init__.py)
│   │   │   ├── BLIP/            ✅ package  (__init__.py)
│   │   │   ├── BLIP2/           ✅ package  (__init__.py)
│   │   │   ├── LLava/           ✅ package  (__init__.py)
│   │   │   ├── Qwen/            ✅ package  (__init__.py)
│   │   │   └── weights/         ❌ ΟΧΙ package (περιέχει .pt αρχεία, όχι .py)
│   │   ├── pipelines/           ✅ package  (__init__.py) ← νέο
│   │   ├── receivers/           ✅ package  (__init__.py) ← νέο
│   │   └── utils/               ✅ package  (__init__.py) ← νέο
│   │       └── server/          ✅ package  (__init__.py) ← νέο
│   ├── scripts/                 ✅ package  (__init__.py)
│   │   └── raspberry_scripts/   ✅ package  (__init__.py)
│   ├── tests/                   ✅ package  (__init__.py)
│   │   ├── pipelines/           ✅ package  (__init__.py)
│   │   └── utils/               ✅ package  (__init__.py)
│   ├── flutter_app/             ❌ ΟΧΙ package (περιέχει .dart, όχι .py)
│   └── waldiez/                 ⚠️  έχει .py αλλά δεν χρησιμοποιείται
│
├── Data/                        ❌ ΟΧΙ package (data files, όχι κώδικας)
└── runs/                        ❌ ΟΧΙ package (YOLO output)
```

---

## Κανόνας: πότε πρέπει να βάλω `__init__.py`

| Φάκελος περιέχει | Πρέπει; |
|-----------------|---------|
| `.py` αρχεία που κάνουν import από άλλα αρχεία | ✅ ΝΑΙ |
| `.py` αρχεία standalone scripts (τρέχουν μόνα τους) | ⚙️ Προαιρετικό |
| `.pt`, `.jpg`, `.json`, `.txt` (data files) | ❌ ΟΧΙ |
| `.dart`, `.html`, `.css` (άλλες γλώσσες) | ❌ ΟΧΙ |

---

## Για το GitHub — τι ανεβαίνει

Τα `__init__.py` **ανεβαίνουν κανονικά στο GitHub**. Είναι μέρος του κώδικα.

```
# .gitignore — ΔΕΝ εξαιρούμε τα __init__.py
# ΔΕΝ γράφουμε: **/__init__.py  ← ΛΑΘΟΣ
```

Τα `__pycache__/` φάκελοι (compiled .pyc) **δεν ανεβαίνουν** και είναι ήδη στο `.gitignore`.

---

## Συνοπτικά

> **`__init__.py` = "αυτός ο φάκελος είναι Python package"**
>
> - Κενό αρχείο = αρκετό για τη λειτουργία
> - Κάθε φάκελος που περιέχει `.py` αρχεία τα οποία γίνονται `import` πρέπει να το έχει
> - Ανεβαίνει στο GitHub
> - Δεν περιέχει λογική (εκτός αν θέλεις re-exports)

