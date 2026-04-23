import json
import logging

import google.generativeai as genai

from src.core.settings import settings
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)


async def evaluator_node(state: SocratesState) -> dict:
    """
    Evaluates the current synthesis and action_draft based on a robust rubric.
    """
    synthesis = state.synthesis
    action_draft = state.action_draft
    selected_model = state.selected_model

    prompt = f"""You are an expert critic and epistemic evaluator. Your goal is to score the following synthesis and draft to ensure they meet the highest standards of clarity, intellectual honesty, and actionability.

Synthesis: {synthesis}
Action Draft: {action_draft}

Score each category from 0 to 2 (0: Poor, 1: Fair, 2: Excellent):
- Clarity: Is the synthesis easy to understand and well-structured?
- Assumptions: Are any hidden assumptions addressed or made explicit?
- Missing Info: Does it clearly state what information is still needed?
- Epistemic Hygiene: Does it avoid overconfidence and distinguish between fact and inference?
- Actionability: Does it provide a concrete next step or path forward?

Return JSON with exactly these keys:
- scores: A dictionary with keys "clarity", "assumptions", "missing_info", "epistemic_hygiene", "actionability" and their integer scores (0-2).
- feedback: A brief (1-2 sentence) justification for the scores and suggestions for improvement."""

    # Configure API key
    genai.configure(api_key=settings.GOOGLE_API_KEY)

    # Use selected model
    model = genai.GenerativeModel(selected_model)

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
    scores = result.get("scores", {})
    feedback = result.get("feedback", "")
    total_score = sum(scores.values())
    passed_eval = total_score >= 7

    retry_count = state.retry_count
    self_correction_notes = state.self_correction_notes
    is_paused = state.is_paused

    if not passed_eval:
        if retry_count < 1:
            retry_count += 1
            self_correction_notes = f"Self-Correction (Retry {retry_count}): {feedback}"
        else:
            is_paused = True

    logger.info(f"Evaluation: total_score={total_score}, passed={passed_eval}, retry={retry_count}")

    return {
        "evaluator_scores": scores,
        "passed_eval": passed_eval,
        "retry_count": retry_count,
        "self_correction_notes": self_correction_notes,
        "is_paused": is_paused,
    }
