import json
import logging

from src.shared.llm_factory import call_llm
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)


async def classify_node(state: SocratesState) -> dict:
    """
    Classifies the user's input using the selected LLM.
    Updates the state with mode, risk_level, and route.
    """
    input_text = state.raw_input

    prompt = f"""You are a master of classification for the Socrates inquiry system. Analyze the user's input and categorize it.
Input: {input_text}

Return JSON with exactly these keys:
- mode: 'refine', 'message', 'decision', or 'analysis'
- risk_level: 'low', 'medium', or 'high'
- route: 'light', 'standard', or 'full'

Heuristics:
- 'light' for simple rewrites, translation, short factual reframing.
- 'standard' for message drafting, moderate interpretation, moderate decision support.
- 'full' for ethical tension, conflict, leadership problems, ambiguous strategic decisions."""

    try:
        response_text = await call_llm(
            prompt=prompt, session_id=state.byok_session_id, response_mime_type="application/json"
        )

        # Parse JSON response
        result = json.loads(response_text)

        # Ensure all required keys are present
        mode = result.get("mode", "refine")
        risk_level = result.get("risk_level", "medium")
        route = result.get("route", "standard")

        logger.info(
            f"Classification: mode={mode}, risk_level={risk_level}, route={route}, model={state.selected_model}"
        )

        return {"mode": mode, "risk_level": risk_level, "route": route}

    except Exception as e:
        logger.error(f"Error in classify_node: {e}")
        # Default fallback values
        return {
            "mode": "refine",
            "risk_level": "medium",
            "route": "standard",
        }
