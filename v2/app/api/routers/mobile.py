

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Response
from typing import Optional
import shutil
from pathlib import Path
from v2.app.config import DATA_DIR, TIME_LOGS, YOLO_ENABLED
from time import perf_counter
from datetime import datetime
import time
import json
import asyncio

from v2.app import state
from starlette.concurrency import run_in_threadpool

router = APIRouter()
UPLOAD_FOLDER = Path(DATA_DIR) / "received_images"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
FIXED_FILENAME = "current_image.jpg"


@router.post("/process")
async def process_image(
    image: UploadFile = File(...),
    src: Optional[str] = Query(default=None, alias="src")
):
    t0 = perf_counter()
    ts0 = datetime.now().isoformat()
    # 1. Save Image
    file_path = UPLOAD_FOLDER / FIXED_FILENAME
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")
    finally:
        await image.close()


    # 2. Call Describe Pipeline (offloaded to thread to keep event loop responsive)
    from v2.app.pipelines.describe import run as run_describe
    try:
        profile: dict = {}
        response = await run_in_threadpool(run_describe, str(file_path), profile=profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in pipeline: {e}")
    finally:
        # Measure end-to-end latency from request reception to description
        elapsed = perf_counter() - t0
        # Persist to timestamps log if enabled
        if TIME_LOGS:
            logs_dir = Path(DATA_DIR) / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_path = logs_dir / "timestamps.csv"
            yolo_sec = float(profile.get("yolo_sec", 0.0)) if isinstance(profile, dict) else 0.0
            desc_sec = float(profile.get("desc_sec", 0.0)) if isinstance(profile, dict) else 0.0
            total_sec = float(elapsed)
            # Create header if file is new/empty
            header = "Time (image received) | Yolo (completed) | Description generated | Total time\n"
            yolo_field = (f"{yolo_sec:.3f}" if YOLO_ENABLED else "-")
            line = f"{ts0} | {yolo_field} | {desc_sec:.3f} | {total_sec:.3f}\n"
            try:
                if not log_path.exists() or log_path.stat().st_size == 0:
                    with log_path.open("w", encoding="utf-8") as f:
                        f.write(header)
                        f.write(line)
                else:
                    with log_path.open("a", encoding="utf-8") as f:
                        f.write(line)
            except Exception:
                # Silent fail for logging to avoid breaking API
                pass

    # 3. Update in-memory state and write-through files (both sources)
    try:
        if isinstance(response, dict):
            # If pipeline ever returns dict, try common keys; else fallback to str(response)
            caption_text = response.get("description") or response.get("caption") or str(response)
        else:
            caption_text = str(response)

        now_epoch = int(time.time())

        src_low = (src or "").lower()
        source = "pi" if src_low == "pi" else "mobile"

        # Update in-memory latest per source
        payload = {"caption": caption_text, "created_at": now_epoch, "source": source}
        state.latest_by_source[source] = payload
        state.last_caption_ts[source] = now_epoch

        # Backward-compat alias for older code
        if source == "pi":
            state.latest_pi = payload
            state.last_seen_pi = now_epoch  # only Pi updates online status
            # Wake status long-pollers
            try:
                if state.status_cond is None:
                    state.status_cond = asyncio.Condition()
                cond = state.status_cond
                async with cond:
                    cond.notify_all()
            except Exception:
                pass

        # Notify long-poll waiters for this source
        try:
            cond = state.caption_cond.get(source)
            if cond is None:
                state.caption_cond[source] = asyncio.Condition()
                cond = state.caption_cond[source]
            async with cond:
                cond.notify_all()
        except Exception:
            pass

        # Write-through artifacts (for reference only, never read on GET)
        gen_dir = Path(DATA_DIR) / "Generated_Text"
        gen_dir.mkdir(parents=True, exist_ok=True)

        # Always maintain a single latest description file (any source)
        latest_txt = gen_dir / "image_description.txt"
        try:
            with latest_txt.open("w", encoding="utf-8") as f:
                f.write(caption_text)
        except Exception:
            pass  # never fail request due to artifact write

        # Keep up to 3 last captions in a single JSON (prepend newest)
        hist_json = gen_dir / "captions.json"
        items = []
        try:
            if hist_json.exists():
                items = json.loads(hist_json.read_text(encoding="utf-8") or "[]")
                if not isinstance(items, list):
                    items = []
        except Exception:
            items = []
        # Prepend new and truncate to max 3
        items = ([payload] + items)[:3]
        try:
            hist_json.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    except Exception:
        # Never fail the request due to state/artifact update issues
        pass

    return {"description": response}

@router.get("/caption_latest")
async def caption_latest(
    since: Optional[int] = Query(default=None),
    source: Optional[str] = Query(default="pi")
):
    """Return latest caption from Raspberry Pi if newer than 'since'.
    - 200: {caption, created_at, source}
    - 204: No Content when no newer caption or none available yet
    """
    src = (source or "pi").lower()
    if src not in state.SOURCES:
        src = "pi"
    latest = state.latest_by_source.get(src)
    if not latest:
        # Nothing in memory yet for this source
        return Response(status_code=204)
    try:
        since_val = int(since) if since is not None else 0
    except Exception:
        since_val = 0

    if since_val >= int(latest.get("created_at", 0)):
        return Response(status_code=204)
    return {
        "caption": latest.get("caption", ""),
        "created_at": int(latest.get("created_at", 0)),
        "source": latest.get("source", src),
    }


@router.get("/caption_next")
async def caption_next(
    source: Optional[str] = Query(default="pi"),
    since: Optional[int] = Query(default=None),
    timeout: int = Query(default=25)
):
    """Long-polling endpoint for next caption.
    - Returns 200 with latest caption when it's newer than 'since'.
    - Waits up to 'timeout' seconds for a new caption; returns 204 on timeout.
    """
    src = (source or "pi").lower()
    if src not in state.SOURCES:
        src = "pi"
    try:
        since_val = int(since) if since is not None else 0
    except Exception:
        since_val = 0

    # Immediate check
    latest = state.latest_by_source.get(src)
    if latest and int(latest.get("created_at", 0)) > since_val:
        return {
            "caption": latest.get("caption", ""),
            "created_at": int(latest.get("created_at", 0)),
            "source": latest.get("source", src),
        }

    # Wait with predicate: wake only when a truly newer caption arrives
    cond = state.caption_cond.get(src)
    if cond is None:
        state.caption_cond[src] = asyncio.Condition()
        cond = state.caption_cond[src]
    safe_timeout = max(1, int(timeout))
    try:
        async with cond:
            await asyncio.wait_for(
                cond.wait_for(lambda: int(state.last_caption_ts.get(src, 0)) > since_val),
                timeout=safe_timeout,
            )
    except asyncio.TimeoutError:
        # No new caption within the timeout window → 204 No Content
        return Response(status_code=204, headers={"X-Reason": "timeout"})
    except Exception:
        # Unexpected server error → 500 Internal Server Error
        return Response(status_code=500)

    # After wake-up, return the latest (guaranteed newer by predicate)
    latest = state.latest_by_source.get(src)
    return {
        "caption": latest.get("caption", "") if latest else "",
        "created_at": int(latest.get("created_at", 0)) if latest else 0,
        "source": latest.get("source", src) if latest else src,
    }
