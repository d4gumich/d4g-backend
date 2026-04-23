import json
import logging

import google.generativeai as genai

from src.core.settings import settings
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)


async def classify_node(state: SocratesState) -> dict:
    """
    Classifies the user's input using Gemini Flash-Lite.
    Updates the state with mode, risk_level, route, and selected_model.
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

    # Use Gemini Flash-Lite for classification
    model = genai.GenerativeModel(settings.SOCRATES_LIGHT_MODEL)

    # Configure API key
    genai.configure(api_key=settings.GOOGLE_API_KEY)

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            candidate_count=1, max_output_tokens=200, temperature=0.0, response_mime_type="application/json"
        ),
    )

    # Parse JSON response
    result = json.loads(response.text)

    # Ensure all required keys are present
    mode = result.get("mode", "refine")
    risk_level = result.get("risk_level", "medium")
    route = result.get("route", "standard")

    # Map risk level to selected model
    if risk_level == "low":
        selected_model = settings.SOCRATES_LIGHT_MODEL
    elif risk_level == "high":
        selected_model = settings.SOCRATES_DEEP_MODEL
    else:
        selected_model = settings.SOCRATES_STANDARD_MODEL

    logger.info(f"Classification: mode={mode}, risk_level={risk_level}, route={route}, model={selected_model}")

    return {"mode": mode, "risk_level": risk_level, "route": route, "selected_model": selected_model}
