import json
import logging

import google.generativeai as genai

from src.core.settings import settings
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)


async def thesis_node(state: SocratesState) -> dict:
    """
    Constructs the strongest good-faith case for the user's current framing.
    """
    input_text = state.refined_question or state.raw_input
    selected_model = state.selected_model

    prompt = f"""You are a master of dialectic reasoning. Construct the strongest, most charitable case (the "thesis") for the following user framing:
Input: {input_text}

Your goal is to represent the user's perspective with intellectual honesty and depth. Focus on the core value and logic that makes this perspective compelling.

Return JSON with exactly this key:
- thesis: the strongest good-faith case for the user's framing."""

    genai.configure(api_key=settings.GOOGLE_API_KEY)
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

        result = json.loads(response.text)
        logger.info("Dialectic: Generated thesis.")
        return {"thesis": result.get("thesis")}

    except Exception as e:
        logger.error(f"Error in thesis_node: {e}")
        return {"thesis": f"Failed to generate thesis: {e}"}


async def antithesis_node(state: SocratesState) -> dict:
    """
    Constructs the strongest credible challenge to the thesis.
    """
    thesis = state.thesis
    selected_model = state.selected_model

    prompt = f"""You are a master of dialectic reasoning. Construct the strongest credible challenge (the "antithesis") to the following thesis:
Thesis: {thesis}

Your goal is not to "win" an argument, but to find the blind spots, risks, and counter-perspectives that the thesis misses. It must be a credible challenge that forces deeper synthesis.

Return JSON with exactly this key:
- antithesis: the strongest credible challenge to the thesis."""

    genai.configure(api_key=settings.GOOGLE_API_KEY)
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

        result = json.loads(response.text)
        logger.info("Dialectic: Generated antithesis.")
        return {"antithesis": result.get("antithesis")}

    except Exception as e:
        logger.error(f"Error in antithesis_node: {e}")
        return {"antithesis": f"Failed to generate antithesis: {e}"}


async def synthesis_node(state: SocratesState) -> dict:
    """
    Combines thesis and antithesis into a grounded conclusion.
    """
    thesis = state.thesis
    antithesis = state.antithesis
    selected_model = state.selected_model

    prompt = f"""You are a master of dialectic reasoning. Combine the following thesis and antithesis into a grounded conclusion (the "synthesis").
Thesis: {thesis}
Antithesis: {antithesis}

Identify what survives the scrutiny of the antithesis, what remains valid from both, and what remains uncertain. Provide a clear path forward.

Return JSON with exactly these keys:
- synthesis: the combined conclusion that accounts for both perspectives
- open_tensions: list of what remains unresolved or uncertain
- next_action: the clearest next step or question to resolve remaining tensions."""

    genai.configure(api_key=settings.GOOGLE_API_KEY)
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

        result = json.loads(response.text)
        logger.info("Dialectic: Generated synthesis.")
        return {
            "synthesis": result.get("synthesis"),
            "open_tensions": result.get("open_tensions", []),
            "next_action": result.get("next_action"),
        }

    except Exception as e:
        logger.error(f"Error in synthesis_node: {e}")
        return {
            "synthesis": f"Failed to generate synthesis: {e}",
            "open_tensions": [],
            "next_action": None,
        }
