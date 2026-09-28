import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.settings import settings

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
