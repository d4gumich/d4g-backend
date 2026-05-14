import logging

import google.generativeai as genai

from src.core.settings import settings

logger = logging.getLogger(__name__)


def make_summary_with_API(all_content, API_key=None):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Get the key
        key = API_key or settings.GOOGLE_API_KEY

        if not key:
            return "⚠️ Google API key not configured."

        genai.configure(api_key=key)
        response = model.generate_content(
            f"Summarize the following text into a concise and structured format: {all_content}",
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=800,
                temperature=0.0,
            ),
        )

        # Return the text content of the response
        return response.text
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
