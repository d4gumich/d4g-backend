from datetime import datetime
from pathlib import Path

import pytest
import yaml

from src.lighthouse.schedule import (
    OneOffWindow,
    Schedule,
    WeeklyWindow,
    build_schedule_payload,
    clamp_pre_wake,
    load_schedule,
)

DETROIT = "America/Detroit"


def _weekly() -> Schedule:
    return Schedule(
        timezone=DETROIT,
        hardware="t4-medium",
        pre_wake_minutes=12,
        drain_minutes=10,
        windows=(
            WeeklyWindow("Tue", "18:00", "20:00"),
            WeeklyWindow("Thu", "18:00", "20:00"),
        ),
        one_off=(),
    )


def at(local_iso: str) -> datetime:
    return datetime.fromisoformat(local_iso)


def test_clamp_pre_wake_bounds():
    assert clamp_pre_wake(12) == 12
    assert clamp_pre_wake(3) == 8
    assert clamp_pre_wake(40) == 25


def test_committed_yaml_is_tue_thu_detroit():
    schedule = load_schedule()
    assert schedule.timezone == "America/Detroit"
    assert schedule.hardware == "t4-medium"
    assert schedule.pre_wake_minutes == 12
    assert schedule.drain_minutes == 10
    assert [(w.weekday, w.start, w.end) for w in schedule.windows] == [
        ("Tue", "18:00", "20:00"),
        ("Thu", "18:00", "20:00"),
    ]
    assert schedule.one_off == ()


def test_loader_clamps_pre_wake(tmp_path: Path):
    path = tmp_path / "schedule.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "timezone": DETROIT,
                "hardware": "t4-medium",
                "pre_wake_minutes": 3,
                "drain_minutes": 10,
                "windows": [{"weekday": "Tue", "start": "18:00", "end": "20:00"}],
                "one_off": [],
            }
        ),
        encoding="utf-8",
    )
    assert load_schedule(path).pre_wake_minutes == 8


def test_loader_rejects_unknown_weekday(tmp_path: Path):
    path = tmp_path / "schedule.yaml"
    path.write_text(
        "timezone: America/Detroit\nhardware: t4-medium\npre_wake_minutes: 12\n"
        "drain_minutes: 10\nwindows:\n  - {weekday: Fun, start: '18:00', end: '20:00'}\n"
        "one_off: []\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="weekday"):
        load_schedule(path)


def test_winter_and_summer_office_hours_are_18_local():
    winter = build_schedule_payload(_weekly(), at("2026-01-06T18:00:00-05:00"))
    summer = build_schedule_payload(_weekly(), at("2026-07-07T18:00:00-04:00"))
    assert winter["phase"] == "open"
    assert summer["phase"] == "open"
    assert winter["current_window"]["start"] == "2026-01-06T23:00:00+00:00"
    assert summer["current_window"]["start"] == "2026-07-07T22:00:00+00:00"


def test_dst_edges_stay_on_local_18():
    spring = build_schedule_payload(_weekly(), at("2026-03-10T18:00:00-04:00"))
    autumn = build_schedule_payload(_weekly(), at("2026-11-03T18:00:00-05:00"))
    assert spring["current_window"]["start"] == "2026-03-10T22:00:00+00:00"
    assert autumn["current_window"]["start"] == "2026-11-03T23:00:00+00:00"


def test_phase_boundaries_for_a_tuesday():
    schedule = _weekly()
    assert build_schedule_payload(schedule, at("2026-01-06T17:47:00-05:00"))["phase"] == "closed"
    pre = build_schedule_payload(schedule, at("2026-01-06T17:48:00-05:00"))
    assert pre["phase"] == "pre_warm"
    assert pre["countdown_to"] == "2026-01-06T23:00:00+00:00"
    assert build_schedule_payload(schedule, at("2026-01-06T18:00:00-05:00"))["phase"] == "open"
    assert build_schedule_payload(schedule, at("2026-01-06T19:49:00-05:00"))["phase"] == "open"
    draining = build_schedule_payload(schedule, at("2026-01-06T19:50:00-05:00"))
    assert draining["phase"] == "drain"
    assert draining["countdown_to"] == "2026-01-07T01:00:00+00:00"
    assert build_schedule_payload(schedule, at("2026-01-06T20:00:00-05:00"))["phase"] == "closed"


def test_closed_countdown_points_at_the_next_start():
    payload = build_schedule_payload(_weekly(), at("2026-01-05T12:00:00-05:00"))
    assert payload["phase"] == "closed"
    assert payload["current_window"] is None
    assert payload["countdown_to"] == "2026-01-06T23:00:00+00:00"
    assert payload["upcoming"][0]["start"] == "2026-01-06T23:00:00+00:00"
    assert len(payload["upcoming"]) == 4
    assert payload["server_time"] == "2026-01-05T17:00:00+00:00"


def test_one_off_replaces_the_weekly_window_on_that_date():
    schedule = Schedule(
        timezone=DETROIT,
        hardware="t4-medium",
        pre_wake_minutes=12,
        drain_minutes=10,
        windows=_weekly().windows,
        one_off=(OneOffWindow("2026-01-06", "12:00", "13:00"),),
    )
    payload = build_schedule_payload(schedule, at("2026-01-06T12:30:00-05:00"))
    assert payload["phase"] == "open"
    assert payload["current_window"]["start"] == "2026-01-06T17:00:00+00:00"


def test_one_off_window_is_included():
    schedule = Schedule(
        timezone=DETROIT,
        hardware="t4-medium",
        pre_wake_minutes=12,
        drain_minutes=10,
        windows=(),
        one_off=(OneOffWindow("2026-10-15", "18:00", "20:00"),),
    )
    payload = build_schedule_payload(schedule, at("2026-10-15T18:30:00-04:00"))
    assert payload["phase"] == "open"
    assert payload["one_off"] == [{"date": "2026-10-15", "start": "18:00", "end": "20:00"}]
