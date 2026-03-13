from __future__ import annotations

import os
import json
from pathlib import Path

from v2.app.config import DATA_DIR, MODEL, PREPROC, YOLO_ENABLED
from v2.app.utils.path_utils import to_rel_path
from time import perf_counter
from v2.app.utils.image_preprocess import preprocess_opencv, preprocess_pillow


def _read_and_preprocess(image_path: str, preproc: str, model: str):
    if model.lower() == "qwen3_vl":
        from PIL import Image
        return Image.open(image_path)

    preproc = (preproc or "opencv").lower()
    if preproc == "opencv":
        import cv2
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError(f"Failed to read image: {image_path}")
        return preprocess_opencv(img_bgr)
    elif preproc == "pillow":
        from PIL import Image
        return preprocess_pillow(Image.open(image_path))
    else:
        raise ValueError(f"Unknown preproc backend: {preproc}")


def _select_model(model_choice: str):
    choice = model_choice.lower()
    if choice == "blip_large":
        from v2.app.models.BLIP.blip_model import load_model, generate_caption
        return "Salesforce/blip-image-captioning-large", load_model, generate_caption
    elif choice == "blip2":
        from v2.app.models.BLIP2.blip2_model import load_model, generate_caption
        return "Salesforce/blip2-opt-2.7b", load_model, generate_caption
    elif choice == "llava":
        from v2.app.models.LLava.llava_model import load_model, generate_caption
        return "llava-hf/llava-1.5-7b-hf", load_model, generate_caption
    elif choice == "qwen3_vl":
        from v2.app.models.Qwen.qwen3_vl_lmstudio import generate_caption
        from v2.app.config import LM_STUDIO_MODEL_NAME
        def _noop_loader(_model_id: str):
            return None, None, None
        return LM_STUDIO_MODEL_NAME, _noop_loader, generate_caption
    else:
        raise ValueError(f"Unsupported model: {model_choice}")


def run(
    image_path: str,
    *,
    model: str = MODEL,
    preproc: str = PREPROC,
    save: bool = True,
    output_path: str | None = None,
    profile: dict | None = None,
) -> str:
    image_path = os.fspath(image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file does not exist: {image_path}")

    model_id, load_model, generate_caption = _select_model(model)
    img_pre = _read_and_preprocess(image_path, preproc, model)

    yolo_dur = 0.0
    context_text: str | None = None
    if YOLO_ENABLED:
        try:
            from v2.app.pipelines.detect import run as run_detect
            t_yolo0 = perf_counter()
            det = run_detect(image_path, task="cross_street")
            yolo_dur = perf_counter() - t_yolo0
            yolo_results = det.get("yolo_results")
            if isinstance(yolo_results, dict):
                context_text = "context_data:\n" + json.dumps(yolo_results, ensure_ascii=False)
            else:
                context_text = "context_data: no traffic lights detected"
        except Exception as e:
            print(f"[WARN] YOLO detect failed: {e}")
            context_text = None
            yolo_dur = 0.0

    processor, mdl, device = load_model(model_id)

    if model.lower() == "qwen3_vl":
        sp_path = (
            Path(DATA_DIR) / "system_prompts_qwen" / "include_yolo_prompt"
            if YOLO_ENABLED
            else Path(DATA_DIR) / "system_prompts_qwen" / "general_prompt"
        )
        system_text = None
        try:
            system_text = sp_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[WARN] Failed to read system prompt from {sp_path}: {e}")
            context_text = "Describe the image concisely."

        t_cap0 = perf_counter()
        caption = generate_caption(
            img_pre, processor, mdl, device,
            system_prompt_text=system_text,
            context_text=context_text,
        )
        cap_dur = perf_counter() - t_cap0
    else:
        if model.lower() == "blip_large":
            print("[INFO] blip_large: continuing without YOLO context.")
        t_cap0 = perf_counter()
        caption = generate_caption(img_pre, processor, mdl, device)
        cap_dur = perf_counter() - t_cap0

    if profile is not None:
        try:
            profile["yolo_sec"] = float(yolo_dur)
            profile["desc_sec"] = float(cap_dur)
        except Exception:
            pass

    if save:
        default_out = Path(DATA_DIR) / "Generated_Text" / "image_description.txt"
        out_path = Path(output_path) if output_path else default_out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(caption)
        print(f"Description saved to {to_rel_path(out_path)}")

    return caption
