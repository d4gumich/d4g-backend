from datetime import datetime, timedelta, timezone

from src.lighthouse.dev_schedule import (
    apply_dev_schedule,
    dev_forwarded,
    dev_open_started,
    dev_preset,
    dev_window,
    fast_forward_dev_window,
    reset_dev_schedule,
    set_dev_preset,
    start_open_clock,
    window_for_preset,
)
from src.lighthouse.schedule import Schedule, WeeklyWindow, build_schedule_payload
from src.lighthouse.seats import claim_seat, reset_seats

NOW = datetime(2026, 9, 29, 18, 0, tzinfo=timezone.utc)


def _schedule(window) -> Schedule:
    return Schedule(
        timezone="America/Detroit",
        hardware="t4-medium",
        pre_wake_minutes=12,
        drain_minutes=10,
        windows=(WeeklyWindow("Tue", "18:00", "20:00"),),
        one_off=(window,),
    )


def test_each_practice_preset_has_the_phase_a_visitor_can_try():
    expected = {
        "soon": "pre_warm",
        "open": "open",
        "drain": "drain",
        "ended": "closed",
    }
    for preset, phase in expected.items():
        payload = build_schedule_payload(_schedule(window_for_preset(preset, NOW)), NOW)
        assert payload["phase"] == phase
    soon = build_schedule_payload(_schedule(window_for_preset("soon", NOW)), NOW)
    start = datetime.fromisoformat(soon["upcoming"][0]["start"])
    assert start - NOW == timedelta(minutes=10)
    reset_dev_schedule()


def test_fast_forward_skips_the_ten_minute_wait_without_leaving_soon():
    reset_dev_schedule()
    set_dev_preset("soon", NOW)
    waiting = dev_window()
    assert waiting is not None
    assert fast_forward_dev_window(NOW) is True
    assert dev_preset() == "soon"
    jumped = dev_window()
    assert jumped is not None
    assert jumped.start != waiting.start
    payload = build_schedule_payload(apply_dev_schedule(_schedule(waiting)), NOW)
    assert payload["phase"] == "open"
    assert fast_forward_dev_window(NOW) is False
    reset_dev_schedule()


def test_fast_forward_marks_the_ten_minute_button_and_a_new_preset_clears_it():
    reset_dev_schedule()
    set_dev_preset("soon", NOW)
    assert dev_forwarded() is False
    assert fast_forward_dev_window(NOW) is True
    assert dev_forwarded() is True
    assert dev_preset() == "soon"
    set_dev_preset("soon", NOW)
    assert dev_forwarded() is False
    reset_dev_schedule()


def test_the_open_clock_stays_parked_until_someone_takes_a_seat():
    reset_dev_schedule()
    reset_seats()
    set_dev_preset("open", NOW)
    parked = dev_window()
    assert parked is not None
    assert dev_open_started() is False
    assert start_open_clock(NOW) is False
    assert dev_window() == parked
    claim_seat("solo", parked.date)
    later = NOW + timedelta(minutes=4)
    assert start_open_clock(later) is True
    assert dev_open_started() is True
    running = dev_window()
    assert running is not None
    assert running.start != parked.start
    assert start_open_clock(later + timedelta(minutes=3)) is False
    assert dev_window() == running
    reset_seats()
    reset_dev_schedule()


def test_a_practice_session_just_after_midnight_stays_on_that_detroit_date():
    now = datetime(2026, 9, 29, 4, 5, tzinfo=timezone.utc)
    window = window_for_preset("open", now)
    assert window.date == "2026-09-29"
    payload = build_schedule_payload(_schedule(window), now)
    assert payload["phase"] == "open"
