from __future__ import annotations

import torch


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def get_dtype() -> torch.dtype:
    device = get_device()
    if device.type in ("cuda", "mps"):
        return torch.float16
    return torch.float32


__all__ = ["get_device", "get_dtype"]

