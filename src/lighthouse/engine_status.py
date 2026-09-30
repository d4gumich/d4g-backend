from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

_LIVE_PHASES = frozenset({"pre_warm", "open", "drain"})
_TTL_SECONDS = 15
_STARTUP_TTL_SECONDS = 3
_lock = threading.Lock()
_cached_at = 0.0
_cached_body: dict | None = None
_startup_started: datetime | None = None
_startup_ready: datetime | None = None
_gpu_test_armed = False

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


def begin_startup_timer(now: datetime, ready_at: datetime | None = None) -> None:
    """Start the dev-mode clock at the wake request. Hugging Face does not time this."""
    global _startup_started, _startup_ready
    _startup_started = now
    _startup_ready = ready_at


def clear_startup_timer() -> None:
    global _startup_started, _startup_ready, _gpu_test_armed
    _startup_started = None
    _startup_ready = None
    _gpu_test_armed = False


def mark_gpu_test_armed() -> None:
    global _gpu_test_armed
    _gpu_test_armed = True


def gpu_test_armed() -> bool:
    return _gpu_test_armed


def note_startup_stage(stage: str | None, now: datetime) -> None:
    global _startup_ready
    if _startup_started is None or _startup_ready is not None:
        return
    if (stage or "").upper() == "RUNNING":
        _startup_ready = now


def startup_report(now: datetime) -> dict | None:
    if _startup_started is None:
        return None
    end = _startup_ready or now
    return {
        "started_at": _startup_started.astimezone(timezone.utc).isoformat(),
        "ready_at": _startup_ready.astimezone(timezone.utc).isoformat() if _startup_ready else None,
        "elapsed_seconds": max(0, int((end - _startup_started).total_seconds())),
    }


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
    pending = _startup_started is not None and _startup_ready is None
    ttl = _STARTUP_TTL_SECONDS if pending else _TTL_SECONDS
    with _lock:
        if _cached_body is not None and moment - _cached_at < ttl:
            return _cached_body

    try:
        status = reader() or {}
    except Exception:
        with _lock:
            if _cached_body is not None:
                return _cached_body
        return _snapshot("UNKNOWN", None, "unknown")

    stage = status.get("stage") or "OFFLINE"
    observed = datetime.now(timezone.utc)
    note_startup_stage(stage, observed)
    step = step_for(stage)
    body = _snapshot(stage, status.get("hardware"), step)
    if step == "waking" and stage.upper() in _DOWN:
        if pending or (_startup_started is not None and _startup_ready is None):
            body["summary"] = "Open now requested the GPU. The timer starts at that request."
        else:
            body["step"] = "asleep"
            body["summary"] = "The engine is still off. The schedule check wakes it during this warmup."
    report = startup_report(observed)
    if report is not None:
        body["startup"] = report
    with _lock:
        _cached_at = moment
        _cached_body = body
    return body
