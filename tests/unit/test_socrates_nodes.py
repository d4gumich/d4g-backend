import json
import random
import string
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.api_core import exceptions

from src.socrates.nodes.action_draft import action_draft_node
from src.socrates.nodes.classify import classify_node
from src.socrates.nodes.dialectic import synthesis_node
from src.socrates.nodes.evaluator import evaluator_node
from src.socrates.nodes.refine import refine_node
from src.socrates.schemas import SocratesState


@pytest.fixture
def base_state():
    return SocratesState(
        raw_input="Should we implement a 4-day work week?",
        session_id="test_session",
        run_id="test_run",
        selected_model="gemini-1.5-flash",
    )


def generate_large_input(chars=5000):
    """Generates a large string to test prompt limits."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=chars))


# --- INPUT STRESS TESTS ---


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stress_input",
    [
        "",  # Empty input
        "   ",  # Whitespace only
        "🤔💭🔥",  # Emojis only
        generate_large_input(10000),  # Large input
        "DELETE FROM users;",  # SQL-injection-like string
        "<script>alert('xss')</script>",  # XSS-like string
    ],
)
async def test_classify_node_input_resilience(base_state, stress_input):
    """Ensures classify_node handles unusual inputs without crashing."""
    base_state.raw_input = stress_input
    mock_response = MagicMock()
    mock_response.text = json.dumps({"mode": "refine", "risk_level": "low", "route": "light"})

    # Patch the API key to satisfy the check in llm_factory
    with patch("src.shared.llm_factory.settings.GOOGLE_API_KEY", "dummy-key"):
        # Using AsyncMock for generate_content_async
        with patch("google.generativeai.GenerativeModel.generate_content_async", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await classify_node(base_state)
            assert result["mode"] == "refine"
            assert result["route"] == "light"


# --- FAILURE & GRPC EDGE CASES ---


@pytest.mark.asyncio
async def test_node_handling_of_specific_grpc_errors(base_state):
    """Simulates a specific gRPC 'ResourceExhausted' error with retry metadata."""
    error_msg = "Quota exceeded for metric: generate_content"
    # Create the actual exception type Gemini throws
    quota_error = exceptions.ResourceExhausted(error_msg)

    with patch("src.shared.llm_factory.settings.GOOGLE_API_KEY", "dummy-key"):
        with patch("google.generativeai.GenerativeModel.generate_content_async", side_effect=quota_error):
            # We expect it to bubble up so the router's stream can yield an error JSON
            with pytest.raises(exceptions.ResourceExhausted) as excinfo:
                await refine_node(base_state)
            assert "Quota exceeded" in str(excinfo.value)


@pytest.mark.asyncio
async def test_action_draft_with_empty_prequisites(base_state):
    """Tests action_draft when previous nodes failed to provide content (empty lists/None)."""
    base_state.synthesis = ""
    base_state.open_tensions = []
    base_state.next_action = None

    mock_response = MagicMock()
    # Updated expectation: result includes summary context
    mock_response.text = json.dumps({"action_draft": "Empty synthesis fallback."})

    with patch("src.shared.llm_factory.settings.GOOGLE_API_KEY", "dummy-key"):
        with patch("google.generativeai.GenerativeModel.generate_content_async", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await action_draft_node(base_state)
            assert "Empty synthesis fallback." in result["action_draft"]


# --- COMPLEX DIALECTIC SCENARIOS ---


@pytest.mark.asyncio
async def test_synthesis_node_complex_integration(base_state):
    """Tests synthesis with a high-fidelity, conflicting set of thesis/antithesis."""
    base_state.thesis = "Decentralizing the database will improve regional latency and user privacy."
    base_state.antithesis = (
        "Decentralization will increase operational complexity, consistency issues, and cost by 300%."
    )

    mock_syn = MagicMock()
    mock_syn.text = json.dumps(
        {
            "synthesis": "Adopt a hybrid Edge-Cache model to improve latency without full database fragmentation.",
            "open_tensions": [
                "Regional regulatory compliance (GDPR)",
                "Developer overhead for multi-region deployments",
            ],
            "next_action": "Conduct a cost-benefit analysis on Cloudflare Workers KV.",
        }
    )

    with patch("src.shared.llm_factory.settings.GOOGLE_API_KEY", "dummy-key"):
        with patch("google.generativeai.GenerativeModel.generate_content_async", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_syn
            result = await synthesis_node(base_state)
            assert len(result["open_tensions"]) == 2
            assert "regulatory" in result["open_tensions"][0]
            assert "Cloudflare" in result["next_action"]


@pytest.mark.asyncio
async def test_evaluator_node_critical_failure_loop(base_state):
    """Verifies evaluator correctly identifies a complete lack of epistemic hygiene."""
    base_state.synthesis = "We should definitely do this because I said so."
    base_state.action_draft = "Just do it."

    # CASE: Total score is 0
    mock_critical_fail = MagicMock()
    mock_critical_fail.text = json.dumps(
        {
            "scores": {"clarity": 0, "assumptions": 0, "missing_info": 0, "epistemic_hygiene": 0, "actionability": 0},
            "feedback": "This is completely unhelpful and arrogant.",
        }
    )

    with patch("src.shared.llm_factory.settings.GOOGLE_API_KEY", "dummy-key"):
        with patch("google.generativeai.GenerativeModel.generate_content_async", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_critical_fail
            result = await evaluator_node(base_state)
            assert result["passed_eval"] is False
            # Ensure it incremented the retry counter for the graph
            assert result["retry_count"] == 1
            assert "Self-Correction" in result["self_correction_notes"]


# --- SCHEMA INTEGRITY ---


def test_socrates_state_validation():
    """Ensures the Pydantic state model enforces constraints correctly."""
    # Invalid mode
    with pytest.raises(ValueError):
        SocratesState(raw_input="Test", session_id="s", run_id="r", mode="invalid_mode")  # type: ignore

    # Missing required fields
    with pytest.raises(ValueError):
        SocratesState()  # type: ignore
