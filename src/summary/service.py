import google.generativeai as genai
from typing import List, Any, Optional
from src.core.config import settings

def make_summary_with_API(all_content: str, api_key: Optional[str] = None) -> str:
    # Use gemini-2.0-flash by default as per summary_generation.py
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    key = api_key or settings.GOOGLE_API_KEY
    if not key:
        return "⚠️ Google API key not configured for summarization."
        
    genai.configure(api_key=key)
    
    try:
        response = model.generate_content(
            f"Summarize the following text into a concise and structured format: {all_content}",  
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=800,
                temperature=0.0,
            ),
        )
        return response.text if hasattr(response, "text") and response.text else "⚠️ Empty response from Gemini."
    except Exception as e:
        return f"⚠️ Summarization failed: {e}"

def combine_all_metadata_into_input(ranked_sentences: List[str], themes_detected: List[str], top_locations: List[Any], disasters: List[Any]) -> str:
    """Combines various metadata into a single prompt for summarization."""
    # Placeholder logic (original source was missing)
    parts = []
    if ranked_sentences:
        parts.append("Key Sentences:\n" + "\n".join(ranked_sentences))
    if themes_detected:
        parts.append("Themes: " + ", ".join(themes_detected))
    if top_locations:
        parts.append("Locations: " + str(top_locations))
    if disasters:
        parts.append("Disasters: " + str(disasters))
        
    return "\n\n".join(parts)

def recursive_summarize(text: str) -> str:
    """Recursively summarizes text. For now, performs a single-pass summary."""
    # Placeholder logic (original source was missing)
    return make_summary_with_API(text)
