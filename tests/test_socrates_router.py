import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_run_socrates_sse():
    mock_event1 = {"classify": {"mode": "refine"}}
    mock_event2 = {"refine": {"refined_question": "What is the goal?"}}

    async def mock_astream(*args, **kwargs):
        yield mock_event1
        yield mock_event2

    with patch("src.socrates.router.socrates_service.graph.astream", side_effect=mock_astream):
        response = client.post("/api/v1/socrates/run", json={"input": "Test input", "channel": "chat"})

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE
        # response.text for streaming response in TestClient works by collecting all data
        lines = response.text.split("\n")
        events = [line[6:] for line in lines if line.startswith("data: ")]

        assert len(events) == 2
        assert json.loads(events[0]) == mock_event1
        assert json.loads(events[1]) == mock_event2


def test_resume_socrates_real():
    mock_event = {"synthesis": {"synthesis": "Resume result"}}

    async def mock_astream(*args, **kwargs):
        # Verify config is passed
        config = args[1] if len(args) > 1 else kwargs.get("config")
        assert config["configurable"]["thread_id"] == "test_session_id"
        yield mock_event

    with patch("src.socrates.router.socrates_service.graph.astream", side_effect=mock_astream):
        response = client.post("/api/v1/socrates/resume/test_session_id")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        lines = response.text.split("\n")
        events = [line[6:] for line in lines if line.startswith("data: ")]

        assert len(events) == 1
        assert json.loads(events[0]) == mock_event
