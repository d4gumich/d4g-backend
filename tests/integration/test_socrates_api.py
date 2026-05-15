import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.core.settings import settings
from src.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Experimental-API-Key": settings.EXPERIMENTAL_ACCESS_KEY}


@pytest.fixture
def mock_session():
    """Mocks the session store to simulate an active AI session."""
    with patch("src.socrates.router.session_store.get_session") as mock:
        mock.return_value = {"provider": "google", "selected_model": "gemini-1.5-flash", "api_key": "test-key"}
        yield mock


def test_run_socrates_full_stream_integration(auth_headers, mock_session):
    """
    Tests the full SSE stream by mocking the underlying graph execution.
    Verifies that all expected node events are yielded with correct data.
    """
    mock_events = [
        {"classify": {"mode": "refine", "route": "standard"}},
        {"refine": {"refined_question": "Should we do X?", "assumptions": ["A1"]}},
        {"thesis": {"thesis": "Yes, because Y."}},
        {"antithesis": {"antithesis": "No, because Z."}},
        {"synthesis": {"synthesis": "Maybe.", "open_tensions": ["T1"]}},
        {"action_draft": {"action_draft": "Next step: Pilot."}},
        {"evaluator": {"passed_eval": True, "evaluator_scores": {"clarity": 2}}},
    ]

    async def mock_astream(*args, **kwargs):
        for event in mock_events:
            yield event

    # Provide a dummy session_id cookie
    cookies = {"session_id": "test-session-id"}

    with patch("src.socrates.router.socrates_service.graph.astream", side_effect=mock_astream):
        response = client.post(
            "/api/v1/products/socrates/run",
            json={"input": "Test input", "channel": "chat"},
            headers=auth_headers,
            cookies=cookies,
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Granular SSE parsing
        lines = response.text.split("\n")
        yielded_data = []
        for line in lines:
            if line.startswith("data: "):
                # Verify each event is valid JSON
                data = json.loads(line[6:])
                yielded_data.append(data)

        assert len(yielded_data) == len(mock_events)
        # Deep data verification
        assert yielded_data[1]["refine"]["assumptions"] == ["A1"]
        assert yielded_data[4]["synthesis"]["open_tensions"] == ["T1"]


def test_run_socrates_mid_stream_crash_recovery(auth_headers, mock_session):
    """
    Simulates a crash (e.g. timeout or sudden disconnect) mid-stream
    to ensure the router yields the partial data + an error event.
    """

    async def mock_astream_crash(*args, **kwargs):
        yield {"classify": {"mode": "full"}}
        yield {"refine": {"refined_question": "Partial success"}}
        # Simulate a sudden failure (e.g. LLM context window exceeded)
        raise RuntimeError("LLM Context window exceeded mid-stream!")

    cookies = {"session_id": "test-session-id"}

    with patch("src.socrates.router.socrates_service.graph.astream", side_effect=mock_astream_crash):
        response = client.post(
            "/api/v1/products/socrates/run", json={"input": "Crash me"}, headers=auth_headers, cookies=cookies
        )

        assert response.status_code == 200

        lines = response.text.split("\n")
        yielded_data = [json.loads(line[6:]) for line in lines if line.startswith("data: ")]

        # Should have partial results followed by an explicit error event
        assert len(yielded_data) == 3
        assert "classify" in yielded_data[0]
        assert "refine" in yielded_data[1]
        assert "error" in yielded_data[2]
        assert "Context window exceeded" in yielded_data[2]["error"]


def test_api_rejection_of_invalid_payloads(auth_headers, mock_session):
    """Verifies the router correctly rejects invalid request bodies before starting the graph."""
    cookies = {"session_id": "test-session-id"}

    # Missing 'input' field
    response = client.post(
        "/api/v1/products/socrates/run", json={"channel": "chat"}, headers=auth_headers, cookies=cookies
    )
    assert response.status_code == 422  # Validation error

    # Empty JSON
    response = client.post("/api/v1/products/socrates/run", json={}, headers=auth_headers, cookies=cookies)
    assert response.status_code == 422


def test_run_socrates_max_quota_immediate_failure(auth_headers, mock_session):
    """
    Simulates the specific 'limit: 0' error where Gemini rejects the very first call.
    Verifies the frontend receives the error immediately to start its 1/3 retry counter.
    """

    async def mock_astream_immediate_fail(*args, **kwargs):
        # No nodes processed, just immediate error
        raise Exception("429 ResourceExhausted: limit: 0, model: gemini-1.5-flash")
        yield {}  # Make it a generator

    cookies = {"session_id": "test-session-id"}

    with patch("src.socrates.router.socrates_service.graph.astream", side_effect=mock_astream_immediate_fail):
        response = client.post(
            "/api/v1/products/socrates/run", json={"input": "Immediate fail"}, headers=auth_headers, cookies=cookies
        )
        assert response.status_code == 200
        assert '{"error": "429 ResourceExhausted: limit: 0' in response.text


def test_resume_socrates_invalid_session(auth_headers):
    """Verifies resume handling for a session that doesn't exist or is corrupted."""

    async def mock_astream_empty(*args, **kwargs):
        # LangGraph returns empty stream if checkpoint is missing
        if False:
            yield {}

    with patch("src.socrates.router.socrates_service.graph.astream", side_effect=mock_astream_empty):
        response = client.post("/api/v1/products/socrates/resume/non_existent_session", headers=auth_headers)
        assert response.status_code == 200
        # Should result in no data events
        assert "data: " not in response.text
