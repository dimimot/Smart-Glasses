"""
Reusable LLaVA captioning wrapper for v2.
"""

from __future__ import annotations

import os
import time
from typing import Any, Tuple

import torch
from transformers import LlavaProcessor, LlavaForConditionalGeneration
from transformers.utils.logging import set_verbosity_error

from v2.app.utils.torch_utils import get_device, get_dtype

# Keep transformers logs quiet
set_verbosity_error()
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")

def load_model(model_id: str = "llava-hf/llava-1.5-7b-hf") -> Tuple[LlavaProcessor, LlavaForConditionalGeneration, torch.device]:
    """Load LLaVA processor and model."""
    device = get_device()
    dtype = get_dtype()

    try:
        processor = LlavaProcessor.from_pretrained(
            model_id,
            use_fast=True,
            local_files_only=True
        )
        model = LlavaForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
            local_files_only=True
        ).to(device)
    except Exception:
        processor = LlavaProcessor.from_pretrained(
            model_id,
            use_fast=True
        )
        model = LlavaForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=dtype,
            low_cpu_mem_usage=True
        ).to(device)
        
    model.eval()
    return processor, model, device

def _clean_generated_text(text: str) -> str:
    if not text:
        return text
    for marker in ["USER:", "User:", "ASSISTANT:", "Assistant:"]:
        text = text.replace(marker, "")
    text = text.replace("Describe the image concisely.", "")
    return " ".join(text.split()).strip()

@torch.inference_mode()
def generate_caption(
    image: Any,
    processor: LlavaProcessor,
    model: LlavaForConditionalGeneration,
    device: torch.device | None = None,
    **gen_kwargs
) -> str:
    """Generate a caption using LLaVA."""
    device = device or next(model.parameters()).device
    
    # Build prompt
    prompt = "Describe the image concisely."
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    prompt_text = processor.apply_chat_template(messages, add_generation_prompt=True)
    
    inputs = processor(images=[image], text=prompt_text, return_tensors="pt").to(device)
    
    output_ids = model.generate(
        **inputs,
        max_new_tokens=gen_kwargs.get("max_new_tokens", 120),
        do_sample=gen_kwargs.get("do_sample", False),
        temperature=gen_kwargs.get("temperature", 0.6),
        top_p=gen_kwargs.get("top_p", 0.9),
    )
    
    # Decode only newly generated tokens
    generated_ids = output_ids[0]
    prompt_len = inputs["input_ids"].shape[1]
    new_tokens = generated_ids[prompt_len:]
    text = processor.batch_decode([new_tokens], skip_special_tokens=True)[0]
    
    return _clean_generated_text(text)

__all__ = ["load_model", "generate_caption"]
