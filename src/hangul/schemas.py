from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class HangulDetectionResponse(BaseModel):
    metadata: Dict[str, Any]
    document_language: Optional[Dict[str, Any]] = None
    document_title: Optional[Any] = None
    document_summary: Optional[str] = None
    content: Optional[List[str]] = None
    report_type: Optional[Any] = None
    locations: Optional[List[Any]] = None
    disasters: Optional[List[Any]] = None
    full_content: Optional[str] = None
    keywords: Optional[List[str]] = None
    markdown_text: Optional[str] = None
    document_theme: Optional[List[str]] = None
    new_detected_disasters: Optional[List[str]] = None
