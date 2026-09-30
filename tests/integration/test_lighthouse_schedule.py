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
TESTER_KEY = "test-key"
TESTER_HEADERS = {"X-Experimental-Api-Key": TESTER_KEY}


@pytest.fixture
def scheduler_token():
    with patch.object(settings, "LIGHTHOUSE_SCHEDULER_TOKEN", "tick-secret"):
        yield "tick-secret"


def test_engine_status_stays_off_hugging_face_until_a_real_session_is_near():
    from src.lighthouse.engine_status import reset_engine_status

    reset_engine_status()
    reset_dev_schedule()
    closed = datetime.fromisoformat("2026-01-05T17:00:00+00:00")
    with (
        patch.object(settings, "LIGHTHOUSE_DEV_SCHEDULE", False),
        patch("src.lighthouse.schedule_router.datetime") as clock,
        patch("src.lighthouse.service.lighthouse_service.get_status") as status,
    ):
        clock.now.return_value = closed
        asleep = client.get("/api/v1/products/lighthouse/schedule/engine")
        assert asleep.status_code == 200
        assert asleep.json()["step"] == "asleep"
        status.assert_not_called()

        clock.now.return_value = datetime.fromisoformat("2026-01-06T22:55:00+00:00")
        status.return_value = {"stage": "APP_STARTING", "hardware": "t4-medium"}
        starting = client.get("/api/v1/products/lighthouse/schedule/engine")
        again = client.get("/api/v1/products/lighthouse/schedule/engine")
        assert starting.json()["step"] == "starting"
        assert again.json()["step"] == "starting"
        assert status.call_count == 1
    reset_engine_status()


def test_a_saved_seat_can_upload_while_the_engine_is_still_starting():
    from src.lighthouse.engine_status import reset_engine_status

    reset_seats()
    reset_dev_schedule()
    reset_engine_status()
    warming = datetime.fromisoformat("2026-01-06T22:55:00+00:00")
    with (
        patch.object(settings, "LIGHTHOUSE_DEV_SCHEDULE", False),
        patch.object(settings, "EXPERIMENTAL_ACCESS_KEY", TESTER_KEY),
        patch("src.lighthouse.schedule_router.datetime") as clock,
        patch("src.lighthouse.service.lighthouse_service.get_status") as status,
        patch("src.lighthouse.service.lighthouse_service.parse_pdf", return_value="Ada Lovelace"),
        patch("src.lighthouse.service.lighthouse_service.analyze") as analyze,
    ):
        clock.now.return_value = warming
        claim = client.post(
            "/api/v1/products/lighthouse/schedule/seats",
            headers=TESTER_HEADERS,
            json={"token": "browser-1", "session": "2026-01-06"},
        )
        assert claim.status_code == 200
        uploaded = client.post(
            "/api/v1/products/lighthouse/schedule/parse",
            headers=TESTER_HEADERS,
            data={"token": "browser-1", "session": "2026-01-06", "sanitize": "false"},
            files={"file": ("resume.pdf", b"%PDF", "application/pdf")},
        )
        assert uploaded.status_code == 200
        assert uploaded.json()["extracted_text"] == "Ada Lovelace"
        stranger = client.post(
            "/api/v1/products/lighthouse/schedule/parse",
            headers=TESTER_HEADERS,
            data={"token": "browser-2", "session": "2026-01-06", "sanitize": "false"},
            files={"file": ("resume.pdf", b"%PDF", "application/pdf")},
        )
        assert stranger.status_code == 403
        assert stranger.json()["detail"] == "A saved seat is required."
        early = client.post(
            "/api/v1/products/lighthouse/schedule/analyze",
            headers=TESTER_HEADERS,
            json={"token": "browser-1", "session": "2026-01-06", "resume_text": "Ada"},
        )
        assert early.status_code == 409
        status.assert_not_called()
        analyze.assert_not_called()

        clock.now.return_value = datetime.fromisoformat("2026-01-06T23:30:00+00:00")
        status.return_value = {"stage": "BUILDING", "hardware": "t4-medium"}
        waiting = client.post(
            "/api/v1/products/lighthouse/schedule/analyze",
            headers=TESTER_HEADERS,
            json={"token": "browser-1", "session": "2026-01-06", "resume_text": "Ada"},
        )
        assert waiting.status_code == 409
        analyze.assert_not_called()
        status.return_value = {"stage": "RUNNING", "hardware": "t4-medium"}
        analyze.return_value = {"status": "success", "extracted_skills": ["Python"]}
        ready = client.post(
            "/api/v1/products/lighthouse/schedule/analyze",
            headers=TESTER_HEADERS,
            json={"token": "browser-1", "session": "2026-01-06", "resume_text": "Ada"},
        )
        assert ready.status_code == 200
        analyze.assert_called_once()
    reset_seats()
    reset_engine_status()


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
    with (
        patch.object(settings, "EXPERIMENTAL_ACCESS_KEY", TESTER_KEY),
        patch("src.lighthouse.service.lighthouse_service.get_status") as status,
    ):
        before = client.get("/api/v1/products/lighthouse/schedule")
        assert before.status_code == 200
        body = before.json()
        assert body["seat_cap"] == 30
        assert body["seats_taken"] == 0
        session = body["seat_session"]
        assert session
        claim = client.post(
            "/api/v1/products/lighthouse/schedule/seats",
            headers=TESTER_HEADERS,
            json={"token": "browser-1", "session": session},
        )
        assert claim.status_code == 200
        claimed = claim.json()
        assert claimed["accepted"] is True
        assert claimed["seats_taken"] == 1
        again = client.post(
            "/api/v1/products/lighthouse/schedule/seats",
            headers=TESTER_HEADERS,
            json={"token": "browser-1", "session": session},
        )
        assert again.json()["seats_taken"] == 1
        after = client.get("/api/v1/products/lighthouse/schedule")
        assert after.json()["seats"][session] == 1
        assert after.json()["seats_taken"] == 1
        bad = client.post(
            "/api/v1/products/lighthouse/schedule/seats",
            headers=TESTER_HEADERS,
            json={"token": "bad token", "session": session},
        )
        assert bad.status_code == 400
        status.assert_not_called()
    reset_seats()


def test_scheduled_seat_requires_the_team_key_and_keeps_the_calendar_public():
    reset_seats()
    with patch.object(settings, "EXPERIMENTAL_ACCESS_KEY", TESTER_KEY):
        schedule = client.get("/api/v1/products/lighthouse/schedule")
        assert schedule.status_code == 200
        session = schedule.json()["seat_session"]
        denied = client.post(
            "/api/v1/products/lighthouse/schedule/seats",
            json={"token": "browser-locked", "session": session},
        )
        assert denied.status_code == 403
        assert denied.json()["detail"] == "A team security key is required for this user test."
        assert client.get("/api/v1/products/lighthouse/schedule").json()["seats"].get(session, 0) == 0
        allowed = client.post(
            "/api/v1/products/lighthouse/schedule/seats",
            headers=TESTER_HEADERS,
            json={"token": "browser-locked", "session": session},
        )
        assert allowed.status_code == 200
        assert allowed.json()["accepted"] is True
    reset_seats()


def test_scheduled_seat_accepts_the_tester_session_cookie():
    reset_seats()
    secure_client = TestClient(app, base_url="https://testserver")
    try:
        with patch.object(settings, "EXPERIMENTAL_ACCESS_KEY", TESTER_KEY):
            opened = secure_client.post(
                "/api/v1/auth/lighthouse-session",
                json={"provider": "hf", "model": "lighthouse", "api_key": TESTER_KEY},
            )
            assert opened.status_code == 200
            schedule = secure_client.get("/api/v1/products/lighthouse/schedule")
            session = schedule.json()["seat_session"]
            claim = secure_client.post(
                "/api/v1/products/lighthouse/schedule/seats",
                json={"token": "browser-cookie", "session": session},
            )
            assert claim.status_code == 200
            secure_client.cookies.clear()
            denied = secure_client.post(
                "/api/v1/products/lighthouse/schedule/seats",
                json={"token": "browser-cookie-2", "session": session},
            )
            assert denied.status_code == 403
    finally:
        secure_client.cookies.clear()
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


def test_open_now_wakes_the_gpu_but_the_scheduler_tick_does_not(scheduler_token):
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
        service.wake_up.assert_called_once_with()
        tick = client.post(
            "/api/v1/products/lighthouse/schedule/tick",
            headers={"X-Scheduler-Token": scheduler_token},
        )
        assert tick.status_code == 200
        assert tick.json()["action"] == "noop"
        service.wake_up.assert_called_once_with()
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
        service.stop_space.assert_called_once_with()
    from src.lighthouse.engine_status import clear_startup_timer

    clear_startup_timer()
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
