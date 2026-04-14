from unittest.mock import MagicMock, patch

import pytest

from src.socrates.nodes.refine import refine_node
from src.socrates.schemas import SocratesState


@pytest.mark.asyncio
async def test_refine_node_success():
    state = SocratesState(
        raw_input="Should I quit my job?",
        session_id="test_session",
        run_id="test_run",
        selected_model="gemini-2.0-flash-lite",
    )

    # Mock the LLM response
    mock_response = MagicMock()
    mock_response.text = '{"refined_question": "Under what conditions would quitting your job align with your long-term goals?", "assumptions": ["Quitting is an option", "You have long-term goals"], "missing_info": ["Current job satisfaction", "Financial situation"]}'

    with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_response):
        result = await refine_node(state)

    assert "refined_question" in result
    assert "assumptions" in result
    assert "missing_info" in result
    assert (
        result["refined_question"] == "Under what conditions would quitting your job align with your long-term goals?"
    )
