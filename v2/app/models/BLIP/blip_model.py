"""
Reusable BLIP captioning wrapper for v2.

API:
- load_model(model_name: str = "blip-large") -> (processor, model, device)
- generate_caption(image, processor, model, device=None, **gen_kwargs) -> str

Notes:
- Accepts image as RGB numpy array or PIL.Image.Image.
- Keeps logging quiet by default.
"""

from __future__ import annotations

from typing import Any, Tuple

import os

from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from transformers.utils.logging import set_verbosity_error

from v2.app.utils.torch_utils import get_device, get_dtype


# Keep transformers logs quiet
set_verbosity_error()
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")


def load_model(model_id: str = "Salesforce/blip-image-captioning-large") -> Tuple[BlipProcessor, BlipForConditionalGeneration, torch.device]:
    """Load BLIP processor+model with local cache preference.

    Returns (processor, model, device)
    """
    device = get_device()
    dtype = get_dtype()

    # Try local cache first for offline usage; fallback to download if allowed
    try:
        processor = BlipProcessor.from_pretrained(model_id, local_files_only=True)
        model = BlipForConditionalGeneration.from_pretrained(model_id, local_files_only=True, torch_dtype=dtype)
    except Exception:
        processor = BlipProcessor.from_pretrained(model_id)
        model = BlipForConditionalGeneration.from_pretrained(model_id, torch_dtype=dtype)

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
    processor: BlipProcessor,
    model: BlipForConditionalGeneration,
    device: torch.device | None = None,
    *,
    max_new_tokens: int = 96,
    num_beams: int = 10,
    repetition_penalty: float = 1.2,
    length_penalty: float = 1.0,
) -> str:
    """Generate a caption for the given image.

    Provide image as RGB numpy array or PIL Image. Returns string caption.
    """
    device = device or next(model.parameters()).device
    pil_image = _to_pil_rgb(image)

    inputs = processor(images=pil_image, return_tensors="pt").to(device)

    output_ids = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        num_beams=num_beams,
        repetition_penalty=repetition_penalty,
        length_penalty=length_penalty,
    )
    caption = processor.batch_decode(output_ids, skip_special_tokens=True)[0]
    return caption.strip()


__all__ = [
    "load_model",
    "generate_caption",
]
