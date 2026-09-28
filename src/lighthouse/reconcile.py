from __future__ import annotations

from datetime import datetime

from src.lighthouse.schedule import Schedule, build_schedule_payload

_ACTIVE = frozenset({"BUILDING", "APP_STARTING", "RUNNING_APP_STARTING", "RUNNING_BUILDING", "RUNNING"})
_ERRORS = frozenset({"BUILD_ERROR", "RUNTIME_ERROR"})
_DOWN = frozenset({"PAUSED", "STOPPED", "SLEEPING", "OFFLINE", ""})


def normalize_hardware(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).strip().lower()
    if "t4" in text and "medium" in text:
        return "t4-medium"
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return text.replace("_", "-")


def decide(phase: str, stage: str | None, hardware: str | None, target: str = "t4-medium") -> str:
    stage_name = (stage or "").upper()
    if stage_name in _ERRORS:
        return "noop"
    on_target = normalize_hardware(hardware) == target
    active = stage_name in _ACTIVE
    if phase in {"pre_warm", "open", "drain"}:
        if active and on_target:
            return "noop"
        return "wake"
    if stage_name in _DOWN:
        return "noop"
    return "stop"


def run_tick(service, schedule: Schedule, now: datetime) -> dict:
    payload = build_schedule_payload(schedule, now)
    try:
        status = service.get_status()
    except Exception as exc:
        detail = getattr(exc, "detail", None) or str(exc)
        return {**payload, "action": "error", "detail": str(detail)}
    action = decide(payload["phase"], status.get("stage"), status.get("hardware"), schedule.hardware)
    try:
        if action == "wake":
            service.wake_up()
        elif action == "stop":
            service.stop_space()
    except Exception as exc:
        detail = getattr(exc, "detail", None) or str(exc)
        return {**payload, "action": "error", "detail": str(detail), "engine_stage": status.get("stage")}
    return {**payload, "action": action, "engine_stage": status.get("stage")}
