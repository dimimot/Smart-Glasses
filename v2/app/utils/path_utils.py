from __future__ import annotations

import os
from pathlib import Path


def to_rel_path(path, include_leading_slash: bool = True) -> str:
    """Return path relative to PROJECT_ROOT for cleaner logs."""
    from v2.app.config import PROJECT_ROOT
    try:
        rel = os.path.relpath(path, PROJECT_ROOT)
        if include_leading_slash and not rel.startswith("/"):
            return "/" + rel
        return rel
    except Exception:
        return str(path)


__all__ = ["to_rel_path"]

