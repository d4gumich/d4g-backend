from typing import Any

from src.shared import summary_generation


def combine_all_metadata_into_input(
    ranked_sentences: list[str], themes_detected: list[str], top_locations: list[Any], disasters: list[Any]
) -> str:
    """Combines various metadata into a single prompt for summarization."""
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


def recursive_summarize(text: str, api_key: str | None = None, model_name: str | None = None) -> str:
    """Recursively summarizes text. For now, performs a single-pass summary."""
    return summary_generation.make_summary_with_API(text, api_key=api_key, model_name=model_name)
