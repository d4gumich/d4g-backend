from pydantic import BaseModel
from typing import List, Optional, Any

class SummaryRequest(BaseModel):
    ranked_sentences: List[str]
    themes_detected: List[str]
    top_locations: List[Any]
    _detected_disasters: List[Any]

class SummaryResponse(BaseModel):
    summary: str
    status: str = "success"
