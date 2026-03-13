from fastapi import APIRouter, Query, Response
from typing import Optional
import asyncio
import time
from v2.app import state

router = APIRouter()

@router.get("/")
async def index():
    return {
        "service": "Smart Glasses Gateway",
        "status": "active",
        "version": "2.0.0",
        "description": "API Gateway for Multi-Agent Image Description System"
    }

@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/api/pi/status")
async def pi_status():
    """Return Raspberry Pi online status based on last_seen timestamp in memory."""
    now = int(time.time())
    last_seen = int(state.last_seen_pi)
    online = (now - last_seen) <= 15 if last_seen > 0 else False
    return {"online": online, "last_seen": last_seen}


@router.get("/api/pi/status_next")
async def pi_status_next(
    since: Optional[int] = Query(default=None),
    timeout: int = Query(default=15)
):
    """Long-polling status endpoint.
    - If current last_seen > since (or since is None), return immediately 200 with status.
    - Else wait up to `timeout` seconds for a status change; return 204 on timeout.
    """
    try:
        since_val = int(since) if since is not None else 0
    except Exception:
        since_val = 0

    def _status_payload():
        now = int(time.time())
        last_seen = int(state.last_seen_pi)
        online = (now - last_seen) <= 15 if last_seen > 0 else False
        return online, last_seen

    online, last_seen = _status_payload()
    if int(last_seen) > since_val:
        return {"online": online, "last_seen": int(last_seen)}

    # Wait for a status change (last_seen update) or timeout
    safe_timeout = max(1, int(timeout))
    # Ensure the condition exists and is bound to the current loop
    if state.status_cond is None:
        state.status_cond = asyncio.Condition()
    cond = state.status_cond
    try:
        async with cond:
            await asyncio.wait_for(
                cond.wait_for(lambda: int(state.last_seen_pi) > since_val),
                timeout=safe_timeout,
            )
    except asyncio.TimeoutError:
        # No status update within the timeout window → 204 No Content
        return Response(status_code=204, headers={"X-Reason": "timeout"})
    except Exception:
        # Unexpected server error → 500 Internal Server Error
        return Response(status_code=500)

    # Re-check and return
    online, last_seen = _status_payload()
    if int(last_seen) > since_val:
        return {"online": online, "last_seen": int(last_seen)}
    return Response(status_code=204)
