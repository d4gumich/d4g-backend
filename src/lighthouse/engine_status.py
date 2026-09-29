from __future__ import annotations

import threading
import time

_LIVE_PHASES = frozenset({"pre_warm", "open", "drain"})
_TTL_SECONDS = 15
_lock = threading.Lock()
_cached_at = 0.0
_cached_body: dict | None = None

_SUMMARIES = {
    "asleep": "The engine is off. The schedule starts it about 12 minutes before the session.",
    "waking": "The schedule is waking the engine.",
    "building": "The engine is building on Hugging Face.",
    "starting": "The engine is starting the app.",
    "ready": "The engine is ready.",
    "error": "The engine hit a problem. The schedule will try again on its next check.",
    "practice": "Practice session. This does not start the GPU. You can upload a resume. Analysis stays off.",
    "unknown": "The engine status could not be read. The schedule still starts it before the session.",
}

_DOWN = frozenset({"PAUSED", "STOPPED", "SLEEPING", "OFFLINE", ""})


def reset_engine_status() -> None:
    global _cached_at, _cached_body
    with _lock:
        _cached_at = 0.0
        _cached_body = None


def step_for(stage: str | None) -> str:
    name = (stage or "").upper()
    if name in {"BUILD_ERROR", "RUNTIME_ERROR"}:
        return "error"
    if name == "RUNNING":
        return "ready"
    if "START" in name:
        return "starting"
    if "BUILD" in name:
        return "building"
    return "waking"


def _snapshot(stage: str | None, hardware: str | None, step: str) -> dict:
    summary = _SUMMARIES[step]
    if step == "waking" and (stage or "").upper() in _DOWN:
        summary = "The engine is still off. The schedule check wakes it during this warmup."
    return {
        "stage": stage,
        "hardware": hardware,
        "step": step,
        "summary": summary,
    }


def engine_snapshot(phase: str, practice: bool, reader, now: float | None = None) -> dict:
    """Return a visitor-facing engine step. Hugging Face is read only while a real session is starting or live."""
    global _cached_at, _cached_body
    if practice:
        return _snapshot("PRACTICE", None, "practice")
    if phase not in _LIVE_PHASES:
        return _snapshot("ASLEEP", None, "asleep")

    moment = time.monotonic() if now is None else now
    with _lock:
        if _cached_body is not None and moment - _cached_at < _TTL_SECONDS:
            return _cached_body

    try:
        status = reader() or {}
    except Exception:
        with _lock:
            if _cached_body is not None:
                return _cached_body
        return _snapshot("UNKNOWN", None, "unknown")

    stage = status.get("stage") or "OFFLINE"
    step = step_for(stage)
    body = _snapshot(stage, status.get("hardware"), step)
    if step == "waking" and stage.upper() in _DOWN:
        body["step"] = "asleep"
        body["summary"] = "The engine is still off. The schedule check wakes it during this warmup."
    with _lock:
        _cached_at = moment
        _cached_body = body
    return body
