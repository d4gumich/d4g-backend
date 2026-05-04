import json
import logging

from src.shared.llm_factory import call_llm
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)


async def action_draft_node(state: SocratesState) -> dict:
    """
    Generates the final user-facing output based on the synthesis and dialectic process using the selected LLM.
    """
    synthesis = state.synthesis
    open_tensions = state.open_tensions
    next_action = state.next_action

    prompt = f"""You are a master of Socratic communication. Based on the synthesis of a dialectic process, generate a clear, honest, and actionable draft for the user.

Synthesis: {synthesis}
Open Tensions: {open_tensions}
Next Recommended Action: {next_action}

Your goal is to provide a response that is not just an answer, but a path forward. Be transparent about what is known, what is uncertain (tensions), and what the next logical step is.

Return JSON with exactly this key:
- action_draft: the final user-facing output."""

    try:
        response_text = await call_llm(
            prompt=prompt, session_id=state.byok_session_id, response_mime_type="application/json"
        )

        # Parse JSON response
        result = json.loads(response_text)

        logger.info("Action Draft: Generated draft.")

        return {
            "action_draft": result.get("action_draft"),
        }

    except Exception as e:
        logger.error(f"Error in action_draft_node: {e}")
        # Fallback value
        return {
            "action_draft": f"Based on our analysis: {synthesis}. Remaining tensions include: {', '.join(open_tensions)}. Next step: {next_action}",
        }
