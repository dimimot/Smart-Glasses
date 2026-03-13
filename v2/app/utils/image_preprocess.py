from __future__ import annotations

from typing import Optional


def preprocess_opencv(image_bgr, upscale_short_side_to: int = 1024):
    """OpenCV preprocessing: denoise → upscale → CLAHE → unsharp mask. Returns RGB array."""
    if image_bgr is None:
        raise ValueError("image_bgr is None")

    import cv2

    img = image_bgr.copy()

    try:
        img = cv2.fastNlMeansDenoisingColored(img, None, h=5, hColor=5, templateWindowSize=7, searchWindowSize=21)
    except Exception:
        pass

    try:
        h, w = img.shape[:2]
        short_side = min(h, w)
        if upscale_short_side_to and short_side < upscale_short_side_to:
            scale = float(upscale_short_side_to) / float(short_side)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    except Exception:
        pass

    try:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        cl = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
        img = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2BGR)
    except Exception:
        pass

    try:
        gaussian = cv2.GaussianBlur(img, (0, 0), sigmaX=1.2)
        img = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
    except Exception:
        pass

    try:
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    except Exception:
        return img


def preprocess_pillow(image_pil, upscale_short_side_to: Optional[int] = 1024):
    """Pillow preprocessing: upscale → unsharp mask. Returns RGB PIL Image."""
    if image_pil is None:
        raise ValueError("image_pil is None")

    from PIL import Image, ImageFilter

    img = image_pil.convert("RGB") if image_pil.mode != "RGB" else image_pil

    try:
        if upscale_short_side_to:
            w, h = img.size
            short_side = min(w, h)
            if short_side < upscale_short_side_to:
                scale = float(upscale_short_side_to) / float(short_side)
                img = img.resize((int(w * scale), int(h * scale)), resample=Image.BICUBIC)
    except Exception:
        pass

    try:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=3))
    except Exception:
        pass

    return img


__all__ = ["preprocess_opencv", "preprocess_pillow"]
