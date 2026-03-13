from __future__ import annotations

from typing import Any, Dict, List, Tuple
import os

import numpy as np
import cv2
from ultralytics import YOLO
from v2.app.config import YOLO_WEIGHTS

_MODEL: YOLO | None = None

# --- Heuristic thresholds ---
MIN_AREA_RATIO_DEFAULT = 0.005
TOP_K_DEFAULT = 2
INNER_CROP_RATIO_DEFAULT = 0.7
HSV_S_MIN_DEFAULT = 120
HSV_V_MIN_DEFAULT = 180


def _read_bgr_imdecode(image_path: str) -> np.ndarray:
    data = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Failed to read image via imdecode: {image_path}")
    return img


def load_model(model_name: str | None = None) -> YOLO:
    global _MODEL
    if _MODEL is None:
        weights = os.fspath(model_name) if model_name else os.fspath(YOLO_WEIGHTS)
        _MODEL = YOLO(weights)
    return _MODEL


def detect_objects(image_path: str, *, model: YOLO | None = None, conf: float = 0.25) -> List[Dict[str, Any]]:
    mdl = model or load_model()
    img_bgr = _read_bgr_imdecode(image_path)
    results = mdl.predict(img_bgr, conf=conf, verbose=False, save=False, save_txt=False, save_conf=False)

    detections: List[Dict[str, Any]] = []
    for r in results:
        names = r.names
        for b in r.boxes:
            cls_id = int(b.cls.item())
            detections.append({
                "class": names.get(cls_id, str(cls_id)),
                "class_id": cls_id,
                "conf": float(b.conf.item()),
                "bbox": [float(x) for x in b.xyxy[0].tolist()],
            })
    return detections


def _bbox_area(b: List[float]) -> float:
    x1, y1, x2, y2 = b
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _bbox_inner_crop(b: List[float], w: int, h: int, ratio: float) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = b
    bw, bh = max(1.0, x2 - x1), max(1.0, y2 - y1)
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    nx1 = int(max(0, min(w - 1, cx - bw * ratio / 2.0)))
    ny1 = int(max(0, min(h - 1, cy - bh * ratio / 2.0)))
    nx2 = int(max(0, min(w - 1, cx + bw * ratio / 2.0)))
    ny2 = int(max(0, min(h - 1, cy + bh * ratio / 2.0)))
    if nx2 <= nx1 or ny2 <= ny1:
        return int(max(0, min(w-1, x1))), int(max(0, min(h-1, y1))), int(max(0, min(w-1, x2))), int(max(0, min(h-1, y2)))
    return nx1, ny1, nx2, ny2


def _bright_mask(hsv: np.ndarray, s_min: int, v_min: int) -> np.ndarray:
    mask_sv = cv2.inRange(hsv, (0, s_min, v_min), (179, 255, 255))
    kernel = np.ones((3, 3), np.uint8)
    return cv2.morphologyEx(cv2.morphologyEx(mask_sv, cv2.MORPH_OPEN, kernel), cv2.MORPH_CLOSE, kernel)


def _hue_masks(hsv: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    red = cv2.bitwise_or(
        cv2.inRange(hsv, (0, 50, 50), (10, 255, 255)),
        cv2.inRange(hsv, (160, 50, 50), (179, 255, 255)),
    )
    green = cv2.inRange(hsv, (40, 50, 50), (90, 255, 255))
    return red, green


def _state_from_hsv(hsv_roi: np.ndarray, s_min: int, v_min: int) -> Tuple[str, float, int, int]:
    if hsv_roi.size == 0:
        return "unknown", 0.0, 0, 0
    bright = _bright_mask(hsv_roi, s_min, v_min)
    if int(bright.sum()) == 0:
        return "unknown", 0.0, 0, 0
    red_mask, green_mask = _hue_masks(hsv_roi)
    red_score = int(cv2.countNonZero(cv2.bitwise_and(red_mask, bright)))
    green_score = int(cv2.countNonZero(cv2.bitwise_and(green_mask, bright)))
    total = red_score + green_score
    if total <= 0:
        return "unknown", 0.0, red_score, green_score
    if red_score > green_score:
        return "red", red_score / (total + 1e-6), red_score, green_score
    elif green_score > red_score:
        return "green", green_score / (total + 1e-6), red_score, green_score
    return "unknown", 0.0, red_score, green_score


def infer_pedestrian_signal_state(
    image_path: str,
    bbox: List[float],
    *,
    inner_crop_ratio: float = INNER_CROP_RATIO_DEFAULT,
    s_min: int = HSV_S_MIN_DEFAULT,
    v_min: int = HSV_V_MIN_DEFAULT,
) -> Dict[str, Any]:
    img_bgr = _read_bgr_imdecode(image_path)
    h, w = img_bgr.shape[:2]
    x1, y1, x2, y2 = [max(0.0, min(float(v), (w if i % 2 == 0 else h) - 1.0)) for i, v in enumerate(bbox)]
    if x2 <= x1 or y2 <= y1:
        return {"state": "unknown", "confidence": 0.0}
    ix1, iy1, ix2, iy2 = _bbox_inner_crop([x1, y1, x2, y2], w, h, inner_crop_ratio)
    roi = img_bgr[iy1:iy2, ix1:ix2]
    if roi.size == 0:
        return {"state": "unknown", "confidence": 0.0}
    state, conf, _, _ = _state_from_hsv(cv2.cvtColor(roi, cv2.COLOR_BGR2HSV), s_min, v_min)
    return {"state": state, "confidence": float(conf)}


def detect_traffic_lights_with_color(image_path: str, *, conf: float = 0.25) -> Dict[str, Any]:
    mdl = load_model()
    all_dets = detect_objects(image_path, model=mdl, conf=conf)
    img_bgr = _read_bgr_imdecode(image_path)
    H, W = img_bgr.shape[:2]

    cand = [d for d in all_dets if d.get("class_id") == 9 or d.get("class") in ("traffic light", "traffic_light")]
    min_area = MIN_AREA_RATIO_DEFAULT * float(W * H)
    cand = sorted([d for d in cand if _bbox_area(d["bbox"]) >= min_area], key=lambda d: _bbox_area(d["bbox"]), reverse=True)[:TOP_K_DEFAULT]

    def _position_of(b: List[float]) -> str:
        cx = (b[0] + b[2]) / 2.0 / max(1.0, float(W))
        return "left" if cx < 1/3 else "right" if cx > 2/3 else "center"

    enriched, signals = [], []
    for d in cand:
        bbox = d["bbox"]
        state_info = infer_pedestrian_signal_state(image_path, bbox)
        state, state_conf = state_info["state"], state_info["confidence"]
        pos = _position_of(bbox)
        enriched.append({**d, "state": state, "state_confidence": state_conf, "position": pos})
        signals.append({"state": state, "confidence": state_conf, "bbox_xyxy": [float(x) for x in bbox], "position": pos})

    primary, summary = None, "unknown"
    if signals:
        best_idx = max(range(len(signals)), key=lambda i: _bbox_area(cand[i]["bbox"]))
        primary = {**signals[best_idx], "selection_reason": "largest_nearby_candidate"}
        summary = primary.get("state", "unknown")

    result: Dict[str, Any] = {
        "detections": enriched,
        "pedestrian_signals": signals,
        "pedestrian_signal": primary,
        "summary_color": summary,
        "status_msg": "ok" if signals else "no traffic lights detected",
    }
    return result


__all__ = ["load_model", "detect_objects", "infer_pedestrian_signal_state", "detect_traffic_lights_with_color"]

