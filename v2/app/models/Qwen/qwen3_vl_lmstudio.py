from __future__ import annotations
from typing import Any
import base64
import io
import json
import os
import requests
from PIL import Image
from v2.app.config import LM_STUDIO_BASE_URL, LM_STUDIO_MODEL_NAME

DEFAULT_GEN_PARAMS = {
    "temperature": 0.1,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "min_p": 0.05,
    "top_p": 0.95,
    "max_tokens": 100,
}


def _to_pil_rgb(image: Any) -> Image.Image:
    if isinstance(image, Image.Image):
        return image.convert("RGB") if image.mode != "RGB" else image
    try:
        import numpy as np  # type: ignore
        if isinstance(image, np.ndarray):
            return Image.fromarray(image)
    except Exception:
        pass
    raise TypeError("Unsupported image type. Provide PIL.Image or RGB numpy array.")


def _image_to_jpeg_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def _build_messages(
    *,
    image_data_url: str,
    system_prompt_text: str | None = None,
    context_text: str | None = None,
    fallback_user_prompt: str | None = None,
):
    messages = []
    if system_prompt_text:
        messages.append({"role": "system", "content": system_prompt_text})

    user_content = []
    if context_text:
        user_content.append({"type": "text", "text": context_text})

    if not system_prompt_text and not context_text:
        text = fallback_user_prompt or "Describe the image concisely as if someone can't see. Do not mention anything regarding picture resolution."
        user_content.append({"type": "text", "text": text})

    user_content.append({"type": "image_url", "image_url": {"url": image_data_url}})

    messages.append({"role": "user", "content": user_content})
    return messages


def _post_chat_completions(payload: dict) -> dict:
    url = f"{LM_STUDIO_BASE_URL.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    resp.raise_for_status()
    return resp.json()


def generate_caption(
    image: Any,
    *_,
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    min_p: float | None = None,
    repeat_penalty: float | None = None,
    presence_penalty: float | None = None,
    frequency_penalty: float | None = None,
    system_prompt_text: str | None = None,
    context_text: str | None = None,
) -> str:
    pil_img = _to_pil_rgb(image)
    data_url = _image_to_jpeg_data_url(pil_img)

    messages = _build_messages(
        image_data_url=data_url,
        system_prompt_text=system_prompt_text,
        context_text=context_text,
        fallback_user_prompt="Describe the image concisely as if someone can't see. Do not mention anything regarding picture resolution.",
    )

    params = DEFAULT_GEN_PARAMS.copy()
    overrides = {
        "max_tokens": max_tokens, "temperature": temperature, "top_p": top_p,
        "top_k": top_k, "min_p": min_p, "repeat_penalty": repeat_penalty,
        "presence_penalty": presence_penalty, "frequency_penalty": frequency_penalty,
    }
    params.update({k: v for k, v in overrides.items() if v is not None})

    payload = {
        "model": LM_STUDIO_MODEL_NAME,
        "messages": messages,
        "stream": False,
        **params,
    }

    data = _post_chat_completions(payload)
    try:
        content = data["choices"][0]["message"]["content"]
        return (content or "").strip()
    except Exception:
        return json.dumps(data)


__all__ = ["generate_caption"]
