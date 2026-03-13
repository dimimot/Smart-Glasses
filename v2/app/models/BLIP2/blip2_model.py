"""
Reusable BLIP‑2 captioning wrapper for v2.

API:
- load_model(model_name: str = "blip2-opt-2.7b") -> (processor, model, device)
- generate_caption(image, processor, model, device=None, **gen_kwargs) -> str

Notes:
- Accepts image as RGB numpy array or PIL.Image.Image.
- Mirrors the logic you used in your BLIP‑2 script (pixel_values -> generate -> tokenizer.decode).
"""

from __future__ import annotations

from typing import Any, Tuple

import os

from PIL import Image
import torch
from transformers import Blip2Processor, Blip2ForConditionalGeneration
from transformers.utils.logging import set_verbosity_error

from v2.app.utils.torch_utils import get_device, get_dtype


# Keep transformers logs quiet
set_verbosity_error()
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")


def load_model(model_id: str = "Salesforce/blip2-opt-2.7b") -> Tuple[Blip2Processor, Blip2ForConditionalGeneration, torch.device]:
    """Load BLIP‑2 processor+model with local cache preference.

    Returns (processor, model, device)
    """
    device = get_device()
    dtype = get_dtype()

    try:
        processor = Blip2Processor.from_pretrained(model_id, local_files_only=True, use_fast=False)
        model = Blip2ForConditionalGeneration.from_pretrained(model_id, local_files_only=True, torch_dtype=dtype)
    except Exception:
        processor = Blip2Processor.from_pretrained(model_id, use_fast=False)
        model = Blip2ForConditionalGeneration.from_pretrained(model_id, torch_dtype=dtype)

    model = model.to(device)
    model.eval()
    return processor, model, device


def _to_pil_rgb(image: Any) -> Image.Image:
    if isinstance(image, Image.Image):
        return image.convert("RGB") if image.mode != "RGB" else image
    # Assume numpy array
    try:
        import numpy as np  # type: ignore
        if isinstance(image, np.ndarray):
            from PIL import Image as PILImage
            return PILImage.fromarray(image)
    except Exception:
        pass
    raise TypeError("Unsupported image type for generate_caption. Provide PIL.Image or RGB numpy array.")


@torch.inference_mode()
def generate_caption(
    image: Any,
    processor: Blip2Processor,
    model: Blip2ForConditionalGeneration,
    device: torch.device | None = None,
    *,
    max_new_tokens: int = 96,
    num_beams: int = 10,
    repetition_penalty: float = 1.2,
    length_penalty: float = 1.0,
) -> str:
    """Generate a caption for the given image using BLIP‑2.

    Matches your existing approach: processor -> pixel_values -> model.generate -> tokenizer.decode.
    """
    device = device or next(model.parameters()).device
    pil_image = _to_pil_rgb(image)

    inputs = processor(images=pil_image, return_tensors="pt")
    pixel_values = inputs.get("pixel_values")
    if pixel_values is None or pixel_values.numel() == 0:
        raise RuntimeError("Processor returned empty pixel_values; cannot caption image.")
    pixel_values = pixel_values.to(device=device, dtype=getattr(model, "dtype", torch.float32))

    output_ids = model.generate(
        pixel_values=pixel_values,
        num_beams=num_beams,
        max_new_tokens=max_new_tokens,
        length_penalty=length_penalty,
        repetition_penalty=repetition_penalty,
        no_repeat_ngram_size=3,
        early_stopping=True,
    )
    caption = processor.tokenizer.decode(output_ids[0], skip_special_tokens=True)
    return caption.strip()


__all__ = [
    "load_model",
    "generate_caption",
]
