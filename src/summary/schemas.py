from typing import Any

from pydantic import BaseModel


class SummaryRequest(BaseModel):
    ranked_sentences: list[str]
    themes_detected: list[str]
    top_locations: list[Any]
    _detected_disasters: list[Any]


class SummaryResponse(BaseModel):
    summary: str
    status: str = "success"
