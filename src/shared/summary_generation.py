import logging

import google.generativeai as genai

from src.core.settings import settings

logger = logging.getLogger(__name__)


def make_summary_with_API(all_content, api_key=None, model_name=None):
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
            response = model.generate_content(
                f"Summarize the following text into a concise and structured format: {all_content}",
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
                response = model.generate_content(
                    f"Summarize the following text into a concise and structured format: {all_content}",
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


# def make_summary_with_API(all_content):
#     document_content = all_content
#     genai.configure(api_key="YOUR KEY HERE")
#     model = genai.GenerativeModel("gemini-2.0-flash-lite-preview-02-05")
#     response = model.generate_content(
#     f"Summarize this content: {document_content}",
#     generation_config=genai.types.GenerationConfig(
#         candidate_count=1,
#         max_output_tokens=800,
#         temperature=0.0,
#         top_p=1,
#         top_k=0,
#         # seed=1,
#     ),
# )
#     # Return the text content of the response
#     return response.text
