import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.lighthouse.schedule import OneOffWindow, Schedule
from src.lighthouse.seats import SEAT_CAP, claim_seat, reset_seats, seat_count

DETROIT = ZoneInfo("America/Detroit")
PRESETS = ("soon", "open", "drain", "ended")

_lock = threading.Lock()
_window: OneOffWindow | None = None
_preset: str | None = None


def reset_dev_schedule() -> None:
    global _preset, _window
    with _lock:
        _window = None
        _preset = None


def dev_preset() -> str | None:
    with _lock:
        return _preset


def dev_window() -> OneOffWindow | None:
    with _lock:
        return _window


def _clock(moment: datetime) -> str:
    return f"{moment.hour:02d}:{moment.minute:02d}"


def _on_date(moment: datetime, day) -> datetime:
    if moment.date() == day:
        return moment
    if moment.date() < day:
        return moment.replace(year=day.year, month=day.month, day=day.day, hour=0, minute=0)
    return moment.replace(year=day.year, month=day.month, day=day.day, hour=23, minute=59)


def window_for_preset(preset: str, now: datetime) -> OneOffWindow:
    if preset not in PRESETS:
        raise ValueError("unknown preset")
    local = now.astimezone(DETROIT).replace(second=0, microsecond=0)
    if preset == "soon":
        start = local + timedelta(minutes=10)
        end = start + timedelta(minutes=30)
    elif preset == "open":
        start = local - timedelta(minutes=15)
        end = local + timedelta(minutes=45)
    elif preset == "drain":
        start = local - timedelta(minutes=40)
        end = local + timedelta(minutes=5)
    else:
        start = local - timedelta(minutes=80)
        end = local - timedelta(minutes=20)
    day = local.date()
    start = _on_date(start, day)
    end = _on_date(end, day)
    if end <= start:
        end = min(start + timedelta(minutes=20), start.replace(hour=23, minute=59))
    return OneOffWindow(day.isoformat(), _clock(start), _clock(end))


def set_dev_preset(preset: str, now: datetime) -> str | None:
    global _preset, _window
    if preset == "clear":
        reset_dev_schedule()
        return None
    window = window_for_preset(preset, now)
    with _lock:
        _window = window
        _preset = preset
    return preset


def apply_dev_schedule(schedule: Schedule) -> Schedule:
    window = dev_window()
    if window is None:
        return schedule
    kept = tuple(item for item in schedule.one_off if item.date != window.date)
    return Schedule(
        timezone=schedule.timezone,
        hardware=schedule.hardware,
        pre_wake_minutes=schedule.pre_wake_minutes,
        drain_minutes=schedule.drain_minutes,
        windows=schedule.windows,
        one_off=(*kept, window),
    )


def fast_forward_dev_window(now: datetime) -> bool:
    """Skip the remaining wait on Starts in 10 min. This does not wake the GPU."""
    global _window
    window = dev_window()
    if dev_preset() != "soon" or window is None:
        return False
    local = now.astimezone(DETROIT).replace(second=0, microsecond=0)
    day = datetime.fromisoformat(window.date).date()
    hour, minute = (int(part) for part in window.start.split(":"))
    current_start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=DETROIT)
    if current_start <= local:
        return False
    start = _on_date(local, day)
    end = _on_date(start + timedelta(minutes=30), day)
    if end <= start:
        end = min(start + timedelta(minutes=20), start.replace(hour=23, minute=59))
    jumped = OneOffWindow(day.isoformat(), _clock(start), _clock(end))
    with _lock:
        _window = jumped
    return True


def fill_dev_seats(session_id: str) -> int:
    for index in range(SEAT_CAP):
        claim_seat(f"dev-fill-{index}", session_id)
    return seat_count(session_id)


def clear_dev_seats() -> None:
    reset_seats()
