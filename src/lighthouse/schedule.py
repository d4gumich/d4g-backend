from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

WEEKDAYS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
DEFAULT_PATH = Path(__file__).with_name("schedule.yaml")


@dataclass(frozen=True)
class WeeklyWindow:
    weekday: str
    start: str
    end: str


@dataclass(frozen=True)
class OneOffWindow:
    date: str
    start: str
    end: str


@dataclass(frozen=True)
class ResolvedWindow:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class Schedule:
    timezone: str
    hardware: str
    pre_wake_minutes: int
    drain_minutes: int
    windows: tuple[WeeklyWindow, ...]
    one_off: tuple[OneOffWindow, ...]


def clamp_pre_wake(minutes: int) -> int:
    return min(25, max(8, minutes))


def _hhmm(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)


def load_schedule(path: Path | None = None) -> Schedule:
    raw = yaml.safe_load((path or DEFAULT_PATH).read_text(encoding="utf-8"))
    windows = []
    for item in raw.get("windows") or []:
        weekday = item["weekday"]
        if weekday not in WEEKDAYS:
            raise ValueError(f"Unknown weekday: {weekday}")
        windows.append(WeeklyWindow(weekday, item["start"], item["end"]))
    one_off = tuple(OneOffWindow(item["date"], item["start"], item["end"]) for item in (raw.get("one_off") or []))
    return Schedule(
        timezone=raw["timezone"],
        hardware=raw["hardware"],
        pre_wake_minutes=clamp_pre_wake(int(raw["pre_wake_minutes"])),
        drain_minutes=int(raw["drain_minutes"]),
        windows=tuple(windows),
        one_off=one_off,
    )


def _local(day, hhmm: str, tz: ZoneInfo) -> datetime:
    hour, minute = _hhmm(hhmm)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)


def upcoming_windows(schedule: Schedule, now: datetime, count: int = 4) -> list[ResolvedWindow]:
    tz = ZoneInfo(schedule.timezone)
    now_local = now.astimezone(tz)
    first = now_local.date() - timedelta(days=1)
    last = now_local.date() + timedelta(days=28)
    found: list[ResolvedWindow] = []
    one_off_by_day = {datetime.fromisoformat(extra.date).date(): extra for extra in schedule.one_off}
    day = first
    while day <= last:
        extra = one_off_by_day.get(day)
        if extra is not None:
            found.append(ResolvedWindow(_local(day, extra.start, tz), _local(day, extra.end, tz)))
        else:
            for window in schedule.windows:
                if day.weekday() != WEEKDAYS[window.weekday]:
                    continue
                found.append(ResolvedWindow(_local(day, window.start, tz), _local(day, window.end, tz)))
        day += timedelta(days=1)
    found.sort(key=lambda item: item.start)
    still_open = [item for item in found if item.end > now]
    return still_open[:count]


def phase_of(window: ResolvedWindow, now: datetime, pre_wake_minutes: int, drain_minutes: int) -> str | None:
    pre_wake_at = window.start - timedelta(minutes=pre_wake_minutes)
    drain_at = window.end - timedelta(minutes=drain_minutes)
    if pre_wake_at <= now < window.start:
        return "pre_warm"
    if window.start <= now < drain_at:
        return "open"
    if drain_at <= now < window.end:
        return "drain"
    return None


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()


def _dump(window: ResolvedWindow) -> dict[str, str]:
    return {"start": _iso(window.start), "end": _iso(window.end)}


def build_schedule_payload(schedule: Schedule, now: datetime) -> dict:
    now = now.astimezone(timezone.utc)
    upcoming = upcoming_windows(schedule, now, count=4)
    current = None
    phase = "closed"
    for window in upcoming:
        found = phase_of(window, now, schedule.pre_wake_minutes, schedule.drain_minutes)
        if found:
            current = window
            phase = found
            break
    if phase == "closed":
        countdown_to = upcoming[0].start if upcoming else None
    elif phase == "pre_warm" and current is not None:
        countdown_to = current.start
    elif current is not None:
        countdown_to = current.end
    else:
        countdown_to = None
    return {
        "server_time": _iso(now),
        "timezone": schedule.timezone,
        "phase": phase,
        "countdown_to": _iso(countdown_to) if countdown_to else None,
        "hardware": schedule.hardware,
        "pre_wake_minutes": schedule.pre_wake_minutes,
        "drain_minutes": schedule.drain_minutes,
        "current_window": _dump(current) if current else None,
        "upcoming": [_dump(window) for window in upcoming],
        "weekly": [{"weekday": item.weekday, "start": item.start, "end": item.end} for item in schedule.windows],
        "one_off": [{"date": item.date, "start": item.start, "end": item.end} for item in schedule.one_off],
    }
