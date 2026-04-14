from unittest.mock import MagicMock, patch

import pytest

from src.socrates.nodes.dialectic import antithesis_node, synthesis_node, thesis_node
from src.socrates.schemas import SocratesState


@pytest.mark.asyncio
async def test_thesis_node_success():
    state = SocratesState(
        raw_input="Should I buy a house?",
        session_id="test_session",
        run_id="test_run",
        selected_model="gemini-2.0-flash",
    )

    mock_response = MagicMock()
    mock_response.text = '{"thesis": "Buying a house is a good investment."}'

    with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_response):
        result = await thesis_node(state)
        assert result["thesis"] == "Buying a house is a good investment."


@pytest.mark.asyncio
async def test_antithesis_node_success():
    state = SocratesState(
        raw_input="Should I buy a house?",
        session_id="test_session",
        run_id="test_run",
        thesis="Buying a house is a good investment.",
        selected_model="gemini-2.0-flash",
    )

    mock_response = MagicMock()
    mock_response.text = '{"antithesis": "Real estate markets can be volatile."}'

    with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_response):
        result = await antithesis_node(state)
        assert result["antithesis"] == "Real estate markets can be volatile."


@pytest.mark.asyncio
async def test_synthesis_node_success():
    state = SocratesState(
        raw_input="Should I buy a house?",
        session_id="test_session",
        run_id="test_run",
        thesis="Buying a house is a good investment.",
        antithesis="Real estate markets can be volatile.",
        selected_model="gemini-2.0-flash",
    )

    mock_response = MagicMock()
    mock_response.text = '{"synthesis": "Buying a house can be good but requires careful timing.", "open_tensions": ["Interest rates"], "next_action": "Check market trends"}'

    with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_response):
        result = await synthesis_node(state)
        assert "synthesis" in result
        assert "open_tensions" in result
        assert "next_action" in result
        assert result["synthesis"] == "Buying a house can be good but requires careful timing."
        assert result["open_tensions"] == ["Interest rates"]
        assert result["next_action"] == "Check market trends"
