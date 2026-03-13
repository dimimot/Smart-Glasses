from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple
import cv2
import numpy as np
from v2.app.models import yolo_model
from datetime import datetime


def run(image_path: str, task: str = "cross-street") -> dict:
    image_path = os.fspath(image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file does not exist: {image_path}")

    print(f"Running YOLO detection on: {image_path} for task: {task}")

    if task in ("cross_street", "cross-street"):
        result = yolo_model.detect_traffic_lights_with_color(image_path)

        signals = result.get("pedestrian_signals", []) or []
        primary = result.get("pedestrian_signal")

        def _upper_state(d: dict | None) -> dict | None:
            if not isinstance(d, dict):
                return None
            out = dict(d)
            out["state"] = (out.get("state") or "").upper()
            return out

        signals_up = [_upper_state(s) for s in signals if isinstance(s, dict)]
        primary_up = _upper_state(primary) if isinstance(primary, dict) else None

        yolo_results = (
            {"traffic_signal": primary_up, "traffic_signals": signals_up}
            if signals_up
            else "no traffic lights detected"
        )

        debug_path = _save_debug_image(image_path, result)

        if isinstance(yolo_results, dict):
            print("[YOLO] traffic_signal:", primary_up)
            for i, s in enumerate(signals_up):
                print(f"[YOLO] #{i+1}: state={s.get('state')} conf={float(s.get('confidence') or 0.0):.2f} pos={s.get('position')} bbox={s.get('bbox_xyxy')}")
        else:
            print("[YOLO] no traffic lights detected")

        return {
            "status": "success",
            "task": task,
            "yolo_results": yolo_results,
            "debug_image": _to_rel_debug_path(debug_path),
        }

    dets = yolo_model.detect_objects(image_path)
    return {"status": "success", "task": task, "yolo_results": {"detections": dets}}


def _imdecode_bgr(image_path: str | Path) -> np.ndarray:
    data = np.fromfile(str(image_path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Failed to read image via imdecode: {image_path}")
    return img


def _draw_box(img: np.ndarray, bbox: Tuple[float, float, float, float], color: Tuple[int, int, int], label: str) -> None:
    x1, y1, x2, y2 = map(int, bbox)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(img, (x1, max(0, y1 - th - baseline - 4)), (x1 + tw + 6, y1), color, -1)
    cv2.putText(img, label, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


def _save_debug_image(image_path: str, result: dict) -> str:
    project_root = Path(__file__).resolve().parents[3]
    out_dir = project_root / "Data" / "Output_image"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "yolo_latest.jpg"

    img = _imdecode_bgr(Path(image_path))
    color_map = {"red": (0, 0, 255), "green": (0, 200, 0), "unknown": (0, 255, 255)}

    for d in result.get("detections", []) or []:
        bbox = d.get("bbox", [0, 0, 0, 0])
        state = d.get("state", "unknown")
        conf = float(d.get("state_confidence", 0.0) or 0.0)
        label = f"{state} {conf:.2f} {d.get('position', '?')}"
        _draw_box(img, tuple(bbox), color_map.get(state, (255, 0, 0)), label)

    cv2.imwrite(str(out_path), img)
    print(f"[YOLO] Debug image saved: {out_path}")
    return str(out_path)


def _to_rel_debug_path(abs_path: str) -> str:
    try:
        project_root = Path(__file__).resolve().parents[3]
        return os.path.relpath(abs_path, project_root)
    except Exception:
        return abs_path
