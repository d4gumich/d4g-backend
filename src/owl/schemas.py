from typing import Any

from pydantic import BaseModel


class OwlQuery(BaseModel):
    text: str
    k: int = 10
    gemini_model: str = "gemini-1.5-flash"
    temperature: float = 0.5
    max_docs: int = 10

class OwlGeminiResponse(BaseModel):
    answer: str
    model: str
    temperature: float

class OwlResponse(BaseModel):
    data: list[dict[str, Any]]
    query: dict[str, Any]
    gemini: OwlGeminiResponse | None = None
    error: str | None = None
