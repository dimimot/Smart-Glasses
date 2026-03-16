from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")

APP_ROOT = Path(__file__).resolve().parent
V2_ROOT = APP_ROOT.parent
PROJECT_ROOT = V2_ROOT.parent

DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "Data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

YOLO_WEIGHTS_DIR = APP_ROOT / "models" / "weights"
YOLO_WEIGHTS = Path(os.environ.get("YOLO_WEIGHTS", YOLO_WEIGHTS_DIR / "yolo26n.pt"))
YOLO_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)


# VLM backend: "qwen3_vl" | "llava" | "blip2" | "blip_large"
MODEL = os.environ.get("MODEL", "qwen3_vl")

# Preprocessing backend: "opencv" | "pillow"
PREPROC = os.environ.get("PREPROC", "opencv")

LM_STUDIO_BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:9094")
LM_STUDIO_MODEL_NAME = os.environ.get("LM_STUDIO_MODEL_NAME", "Qwen3-VL-8B-Instruct-MLX-4bit")

TIME_LOGS = os.environ.get("TIME_LOGS", "ON").strip().upper() == "ON"
YOLO_ENABLED = os.environ.get("YOLO_ENABLED", "OFF").strip().upper() == "ON"

__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "MODEL",
    "PREPROC",
    "LM_STUDIO_BASE_URL",
    "LM_STUDIO_MODEL_NAME",
    "YOLO_WEIGHTS",
    "TIME_LOGS",
    "YOLO_ENABLED",
]
