import json
import logging

import google.generativeai as genai

from src.core.settings import settings
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)


async def refine_node(state: SocratesState) -> dict:
    """
    Refines the user's input using Gemini.
    Returns a dictionary with refined_question, assumptions, and missing_info.
    """
    input_text = state.raw_input
    selected_model = state.selected_model

    prompt = f"""You are a master of Socratic refinement. Analyze the user's input and transform it into a stronger, clearer question. Identify hidden assumptions and missing information needed for a grounded answer.
Input: {input_text}

Return JSON with exactly these keys:
- refined_question: the stronger question
- assumptions: list of identified assumptions
- missing_info: list of information needed to move forward

Success criteria: A strong refine output should make the next reasoning step easier, narrower, and more honest."""

    # Configure API key
    genai.configure(api_key=settings.GOOGLE_API_KEY)

    # Use selected model
    model = genai.GenerativeModel(selected_model)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=1000,
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )

        # Parse JSON response
        result = json.loads(response.text)

        logger.info(f"Refinement: refined_question={result.get('refined_question')}")

        return {
            "refined_question": result.get("refined_question"),
            "assumptions": result.get("assumptions", []),
            "missing_info": result.get("missing_info", []),
        }

    except Exception as e:
        logger.error(f"Error in refine_node: {e}")
        # Fallback values
        return {
            "refined_question": input_text,
            "assumptions": [],
            "missing_info": [],
        }
