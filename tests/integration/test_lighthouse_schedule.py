import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.settings import settings
from src.lighthouse.dev_schedule import reset_dev_schedule
from src.lighthouse.seats import reset_seats

with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@pytest.fixture
def scheduler_token():
    with patch.object(settings, "LIGHTHOUSE_SCHEDULER_TOKEN", "tick-secret"):
        yield "tick-secret"


def test_schedule_is_public_and_does_not_touch_huggingface():
    fixed = datetime.fromisoformat("2026-01-05T17:00:00+00:00")
    with (
        patch("src.lighthouse.schedule_router.datetime") as clock,
        patch("src.lighthouse.service.lighthouse_service.get_status") as status,
    ):
        clock.now.return_value = fixed
        response = client.get("/api/v1/products/lighthouse/schedule")
    assert response.status_code == 200
    body = response.json()
    assert body["server_time"] == "2026-01-05T17:00:00+00:00"
    assert body["phase"] == "closed"
    assert body["countdown_to"] == "2026-01-06T23:00:00+00:00"
    assert body["timezone"] == "America/Detroit"
    status.assert_not_called()


def test_seat_claim_counts_one_browser_once_and_does_not_touch_huggingface():
    reset_seats()
    with patch("src.lighthouse.service.lighthouse_service.get_status") as status:
        before = client.get("/api/v1/products/lighthouse/schedule")
        assert before.status_code == 200
        body = before.json()
        assert body["seat_cap"] == 30
        assert body["seats_taken"] == 0
        session = body["seat_session"]
        assert session
        claim = client.post(
            "/api/v1/products/lighthouse/schedule/seats",
            json={"token": "browser-1", "session": session},
        )
        assert claim.status_code == 200
        claimed = claim.json()
        assert claimed["accepted"] is True
        assert claimed["seats_taken"] == 1
        again = client.post(
            "/api/v1/products/lighthouse/schedule/seats",
            json={"token": "browser-1", "session": session},
        )
        assert again.json()["seats_taken"] == 1
        after = client.get("/api/v1/products/lighthouse/schedule")
        assert after.json()["seats"][session] == 1
        assert after.json()["seats_taken"] == 1
        bad = client.post(
            "/api/v1/products/lighthouse/schedule/seats",
            json={"token": "bad token", "session": session},
        )
        assert bad.status_code == 400
        status.assert_not_called()
    reset_seats()


def test_dev_controls_stay_off_unless_the_local_flag_is_set():
    reset_dev_schedule()
    with patch.object(settings, "LIGHTHOUSE_DEV_SCHEDULE", False):
        hidden = client.post(
            "/api/v1/products/lighthouse/schedule/dev",
            json={"preset": "open"},
        )
        assert hidden.status_code == 404
        body = client.get("/api/v1/products/lighthouse/schedule").json()
        assert "dev" not in body


def test_dev_open_session_does_not_wake_the_gpu(scheduler_token):
    reset_dev_schedule()
    reset_seats()
    fixed = datetime.fromisoformat("2026-01-06T20:01:00-05:00")
    with (
        patch.object(settings, "LIGHTHOUSE_DEV_SCHEDULE", True),
        patch("src.lighthouse.schedule_router.datetime") as clock,
        patch("src.lighthouse.schedule_router.lighthouse_service") as service,
    ):
        clock.now.return_value = fixed
        service.get_status.return_value = {"stage": "PAUSED", "hardware": "cpu-basic"}
        opened = client.post(
            "/api/v1/products/lighthouse/schedule/dev",
            json={"preset": "open"},
        )
        assert opened.status_code == 200
        body = opened.json()
        assert body["dev"] is True
        assert body["dev_preset"] == "open"
        assert body["phase"] == "open"
        assert body["dev_date"] == "2026-01-06"
        tick = client.post(
            "/api/v1/products/lighthouse/schedule/tick",
            headers={"X-Scheduler-Token": scheduler_token},
        )
        assert tick.status_code == 200
        assert tick.json()["action"] == "noop"
        service.wake_up.assert_not_called()
        service.stop_space.assert_not_called()
        filled = client.post(
            "/api/v1/products/lighthouse/schedule/dev",
            json={"preset": "fill_seats", "session": "2026-01-06"},
        )
        assert filled.json()["seats"]["2026-01-06"] == 30
        cleared = client.post(
            "/api/v1/products/lighthouse/schedule/dev",
            json={"preset": "reset_seats"},
        )
        assert cleared.json()["seats"].get("2026-01-06", 0) == 0
        restored = client.post(
            "/api/v1/products/lighthouse/schedule/dev",
            json={"preset": "clear"},
        )
        assert restored.json()["dev_preset"] is None
        assert restored.json()["phase"] == "closed"
    reset_dev_schedule()
    reset_seats()


def test_tick_without_token_is_403(scheduler_token):
    response = client.post("/api/v1/products/lighthouse/schedule/tick")
    assert response.status_code == 403


def test_tick_with_wrong_token_is_403(scheduler_token):
    response = client.post(
        "/api/v1/products/lighthouse/schedule/tick",
        headers={"X-Scheduler-Token": "nope"},
    )
    assert response.status_code == 403


def test_tick_when_token_unconfigured_is_503():
    with patch.object(settings, "LIGHTHOUSE_SCHEDULER_TOKEN", None):
        response = client.post(
            "/api/v1/products/lighthouse/schedule/tick",
            headers={"X-Scheduler-Token": "tick-secret"},
        )
    assert response.status_code == 503


def test_tick_with_token_stops_a_live_space_after_hours(scheduler_token):
    fixed = datetime.fromisoformat("2026-01-06T20:01:00-05:00")
    with (
        patch("src.lighthouse.schedule_router.datetime") as clock,
        patch("src.lighthouse.schedule_router.lighthouse_service") as service,
    ):
        clock.now.return_value = fixed
        service.get_status.return_value = {"stage": "RUNNING", "hardware": "t4-medium"}
        response = client.post(
            "/api/v1/products/lighthouse/schedule/tick",
            headers={"X-Scheduler-Token": scheduler_token},
        )
    assert response.status_code == 200
    assert response.json()["action"] == "stop"
    service.stop_space.assert_called_once_with()
    service.wake_up.assert_not_called()


def test_cli_tick_prints_action(capsys):
    from src.lighthouse.cli import main

    with patch("src.lighthouse.cli.run_tick", return_value={"action": "noop", "phase": "closed"}):
        assert main(["tick"]) == 0
    assert json.loads(capsys.readouterr().out)["action"] == "noop"

    with patch("src.lighthouse.cli.run_tick", return_value={"action": "error", "detail": "down"}):
        assert main(["tick"]) == 1
    assert json.loads(capsys.readouterr().out)["action"] == "error"
