from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

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
    data: List[Dict[str, Any]]
    query: Dict[str, Any]
    gemini: Optional[OwlGeminiResponse] = None
    error: Optional[str] = None
