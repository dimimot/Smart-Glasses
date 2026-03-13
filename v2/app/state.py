from typing import Any, Dict, Optional
import asyncio

SOURCES = ("pi", "mobile")

latest_by_source: Dict[str, Optional[Dict[str, Any]]] = {s: None for s in SOURCES}
latest_pi: Optional[Dict[str, Any]] = None
last_caption_ts: Dict[str, int] = {s: 0 for s in SOURCES}

# Initialized on startup to avoid event loop issues
caption_cond: Dict[str, asyncio.Condition] = {}
last_seen_pi: int = 0
status_cond: Optional[asyncio.Condition] = None


def init_async_primitives() -> None:
    """Initialize asyncio conditions bound to the running event loop (call from startup)."""
    global caption_cond, status_cond
    for s in SOURCES:
        if s not in caption_cond:
            caption_cond[s] = asyncio.Condition()
    if status_cond is None:
        status_cond = asyncio.Condition()
