import json
import logging

from src.shared.llm_factory import call_llm
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)


async def refine_node(state: SocratesState) -> dict:
    """
    Refines the user's input using the selected LLM.
    Returns a dictionary with refined_question, assumptions, and missing_info.
    """
    input_text = state.raw_input

    prompt = f"""You are a master of Socratic refinement. Analyze the user's input and transform it into a stronger, clearer question. Identify hidden assumptions and missing information needed for a grounded answer.
Input: {input_text}

Return JSON with exactly these keys:
- refined_question: the stronger question
- assumptions: list of identified assumptions
- missing_info: list of information needed to move forward

Success criteria: A strong refine output should make the next reasoning step easier, narrower, and more honest."""

    response_text = await call_llm(
        prompt=prompt, session_id=state.byok_session_id, response_mime_type="application/json"
    )

    # Parse JSON response
    result = json.loads(response_text)

    logger.info(f"Refinement: refined_question={result.get('refined_question')}")

    return {
        "refined_question": result.get("refined_question"),
        "assumptions": result.get("assumptions", []),
        "missing_info": result.get("missing_info", []),
    }
