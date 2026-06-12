import logging

from src.core.settings import settings

logger = logging.getLogger(__name__)


def make_summary_with_API(all_content, api_key=None, model_name=None):
    import google.generativeai as genai

    try:
        # Get the key
        key = api_key or settings.GOOGLE_API_KEY

        if not key:
            return "⚠️ Google API key not configured."

        # Ensure global state is set to THIS call's key
        genai.configure(api_key=key)

        model_id = model_name or settings.SOCRATES_STANDARD_MODEL

        try:
            model = genai.GenerativeModel(model_id)
            prompt = (
                f"Provide a concise, high-level professional summary of the following document content. "
                f"Synthesize the most important information, key achievements, or main findings into a clear overview. "
                f"Do NOT simply reformat or repeat the entire text. Limit the response to 2-3 short paragraphs maximum. "
                f"Return ONLY the summary text itself—no conversational filler like 'Here is a summary'.\n\n"
                f"Text:\n{all_content}"
            )
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=800,
                    temperature=0.0,
                ),
            )
            return response.text
        except Exception as e:
            # Fallback for 404 or other model-specific errors
            err_str = str(e).lower()
            if "404" in err_str or "not found" in err_str:
                logger.warning(f"Model {model_id} failed with 404, falling back to gemini-1.5-flash")
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = (
                    f"Provide a concise, high-level professional summary of the following document content. "
                    f"Synthesize the most important information, key achievements, or main findings into a clear overview. "
                    f"Do NOT simply reformat or repeat the entire text. Limit the response to 2-3 short paragraphs maximum. "
                    f"Return ONLY the summary text itself—no conversational filler like 'Here is a summary'.\n\n"
                    f"Text:\n{all_content}"
                )
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        max_output_tokens=800,
                        temperature=0.0,
                    ),
                )
                return response.text
            raise e

    except Exception as e:
        logger.error(f"make_summary_with_API failed: {e}")
        return f"⚠️ Summarization failed: {e}"
