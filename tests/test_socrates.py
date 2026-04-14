import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.socrates.schemas import SocratesState

client = TestClient(app)


@pytest.fixture
def mock_gemini():
    with patch("google.generativeai.GenerativeModel.generate_content") as mock:
        yield mock


@pytest.mark.asyncio
async def test_socrates_light_path(mock_gemini):
    """
    Tests the 'light' path: INTAKE -> CLASSIFY -> ACTION_DRAFT -> END.
    It should skip refine, thesis, antithesis, and synthesis.
    """
    # 1. Setup mocks for each node
    def side_effect(prompt, **kwargs):
        mock_response = MagicMock()
        if "master of classification" in prompt:
            mock_response.text = json.dumps({
                "mode": "refine",
                "risk_level": "low",
                "route": "light"
            })
        elif "master of Socratic communication" in prompt:
            mock_response.text = json.dumps({
                "action_draft": "Lightweight response to: I is hungry"
            })
        else:
            # If it reaches other nodes, we want to know
            mock_response.text = json.dumps({"error": f"Unexpected node call: {prompt[:50]}"})
        return mock_response

    mock_gemini.side_effect = side_effect

    # 2. Call the endpoint
    response = client.post(
        "/api/v1/socrates/run",
        json={"input": "Correct the grammar in this message: 'I is hungry'", "session_id": "test_light"}
    )

    assert response.status_code == 200
    
    # 3. Verify streaming response
    events = []
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    # 4. Verify graph transitions
    node_names = [list(event.keys())[0] for event in events]
    
    # Expected nodes for light path
    assert "classify" in node_names
    assert "action_draft" in node_names
    
    # Nodes that should be SKIPPED in light path
    assert "refine" not in node_names
    assert "thesis" not in node_names
    assert "antithesis" not in node_names
    assert "synthesis" not in node_names
    assert "evaluator" not in node_names

    # 5. Verify final output
    final_event = events[-1]
    assert "action_draft" in final_event
    assert "Lightweight response" in final_event["action_draft"]["action_draft"]


@pytest.mark.asyncio
async def test_socrates_standard_path(mock_gemini):
    """
    Tests the 'standard' path: CLASSIFY -> REFINE -> THESIS -> ANTITHESIS -> SYNTHESIS -> ACTION_DRAFT -> EVALUATOR -> END.
    Standard path visits all nodes.
    """
    def side_effect(prompt, **kwargs):
        mock_response = MagicMock()
        if "master of classification" in prompt:
            mock_response.text = json.dumps({
                "mode": "refine",
                "risk_level": "medium",
                "route": "standard"
            })
        elif "refine" in prompt:
            mock_response.text = json.dumps({"refined_input": "Moderate risk input"})
        elif "thesis" in prompt:
            mock_response.text = json.dumps({"thesis": "Thesis for moderate risk"})
        elif "antithesis" in prompt:
            mock_response.text = json.dumps({"antithesis": "Antithesis for moderate risk"})
        elif "synthesis" in prompt:
            mock_response.text = json.dumps({"synthesis": "Synthesis for moderate risk"})
        elif "master of Socratic communication" in prompt:
            mock_response.text = json.dumps({"action_draft": "Action draft for moderate risk"})
        elif "evaluator" in prompt:
            mock_response.text = json.dumps({"score": 0.9, "feedback": "Pass", "passed": True})
        else:
            mock_response.text = json.dumps({"error": f"Unexpected node call: {prompt[:50]}"})
        return mock_response

    mock_gemini.side_effect = side_effect

    response = client.post(
        "/api/v1/socrates/run",
        json={"input": "Moderate risk query", "session_id": "test_standard"}
    )

    assert response.status_code == 200
    
    events = []
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    node_names = [list(event.keys())[0] for event in events]
    
    assert "classify" in node_names
    assert "refine" in node_names
    assert "thesis" in node_names
    assert "antithesis" in node_names
    assert "synthesis" in node_names
    assert "action_draft" in node_names
    assert "evaluator" in node_names


@pytest.mark.asyncio
async def test_socrates_full_path(mock_gemini):
    """
    Tests the 'full' path: CLASSIFY -> REFINE -> THESIS -> ANTITHESIS -> SYNTHESIS -> ACTION_DRAFT -> EVALUATOR -> END.
    Full path also visits all nodes (like standard, but with higher risk).
    """
    def side_effect(prompt, **kwargs):
        mock_response = MagicMock()
        if "master of classification" in prompt:
            mock_response.text = json.dumps({
                "mode": "refine",
                "risk_level": "high",
                "route": "full"
            })
        elif "refine" in prompt:
            mock_response.text = json.dumps({"refined_input": "High risk input"})
        elif "thesis" in prompt:
            mock_response.text = json.dumps({"thesis": "Thesis for high risk"})
        elif "antithesis" in prompt:
            mock_response.text = json.dumps({"antithesis": "Antithesis for high risk"})
        elif "synthesis" in prompt:
            mock_response.text = json.dumps({"synthesis": "Synthesis for high risk"})
        elif "master of Socratic communication" in prompt:
            mock_response.text = json.dumps({"action_draft": "Action draft for high risk"})
        elif "evaluator" in prompt:
            mock_response.text = json.dumps({"score": 0.95, "feedback": "Pass", "passed": True})
        else:
            mock_response.text = json.dumps({"error": f"Unexpected node call: {prompt[:50]}"})
        return mock_response

    mock_gemini.side_effect = side_effect

    response = client.post(
        "/api/v1/socrates/run",
        json={"input": "High risk query", "session_id": "test_full"}
    )

    assert response.status_code == 200
    
    events = []
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    node_names = [list(event.keys())[0] for event in events]
    
    assert "classify" in node_names
    assert "refine" in node_names
    assert "thesis" in node_names
    assert "antithesis" in node_names
    assert "synthesis" in node_names
    assert "action_draft" in node_names
    assert "evaluator" in node_names
