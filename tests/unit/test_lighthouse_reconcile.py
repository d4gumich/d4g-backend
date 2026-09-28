from datetime import datetime
from unittest.mock import MagicMock

from fastapi import HTTPException

from src.lighthouse.reconcile import decide, run_tick
from src.lighthouse.schedule import Schedule, WeeklyWindow


def _schedule() -> Schedule:
    return Schedule(
        timezone="America/Detroit",
        hardware="t4-medium",
        pre_wake_minutes=12,
        drain_minutes=10,
        windows=(WeeklyWindow("Tue", "18:00", "20:00"),),
        one_off=(),
    )


def test_decide_matrix():
    assert decide("open", "RUNNING", "t4-medium") == "noop"
    assert decide("open", "RUNNING_APP_STARTING", "t4-medium") == "noop"
    assert decide("pre_warm", "APP_STARTING", "t4-medium") == "noop"
    assert decide("drain", "RUNNING", "t4-medium") == "noop"
    assert decide("open", "PAUSED", "cpu-basic") == "wake"
    assert decide("open", "RUNNING", "cpu-basic") == "wake"
    assert decide("pre_warm", "OFFLINE", "") == "wake"
    assert decide("closed", "RUNNING", "t4-medium") == "stop"
    assert decide("closed", "APP_STARTING", "t4-medium") == "stop"
    assert decide("closed", "PAUSED", "t4-medium") == "noop"
    assert decide("closed", "PAUSED", "cpu-basic") == "noop"
    assert decide("open", "BUILD_ERROR", "t4-medium") == "noop"
    assert decide("open", "RUNTIME_ERROR", "cpu-basic") == "noop"
    assert decide("closed", "OFFLINE", None) == "noop"


def test_run_tick_wakes_during_pre_warm():
    service = MagicMock()
    service.get_status.return_value = {"stage": "PAUSED", "hardware": "cpu-basic"}
    result = run_tick(service, _schedule(), datetime.fromisoformat("2026-01-06T17:48:00-05:00"))
    assert result["phase"] == "pre_warm"
    assert result["action"] == "wake"
    service.wake_up.assert_called_once_with()
    service.stop_space.assert_not_called()


def test_run_tick_does_not_wake_a_live_open_session():
    service = MagicMock()
    service.get_status.return_value = {"stage": "RUNNING", "hardware": "t4-medium"}
    result = run_tick(service, _schedule(), datetime.fromisoformat("2026-01-06T18:30:00-05:00"))
    assert result["action"] == "noop"
    assert result["engine_stage"] == "RUNNING"
    service.wake_up.assert_not_called()
    service.stop_space.assert_not_called()


def test_run_tick_stops_after_the_window():
    service = MagicMock()
    service.get_status.return_value = {"stage": "RUNNING", "hardware": "t4-medium"}
    result = run_tick(service, _schedule(), datetime.fromisoformat("2026-01-06T20:01:00-05:00"))
    assert result["phase"] == "closed"
    assert result["action"] == "stop"
    service.stop_space.assert_called_once_with()


def test_run_tick_reports_status_failure_without_calling_wake():
    service = MagicMock()
    service.get_status.side_effect = HTTPException(status_code=502, detail="HF API Error")
    result = run_tick(service, _schedule(), datetime.fromisoformat("2026-01-06T18:30:00-05:00"))
    assert result["action"] == "error"
    assert "HF API Error" in result["detail"]
    service.wake_up.assert_not_called()
