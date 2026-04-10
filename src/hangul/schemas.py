from typing import Any

from pydantic import BaseModel


class HangulDetectionResponse(BaseModel):
    metadata: dict[str, Any]
    document_language: dict[str, Any] | None = None
    document_title: Any | None = None
    document_summary: str | None = None
    content: list[str] | None = None
    report_type: Any | None = None
    locations: dict[str, Any] | None = None
    disasters: list[Any] | None = None
    full_content: str | None = None
    keywords: list[str] | None = None
    markdown_text: str | None = None
    document_theme: list[str] | None = None
    new_detected_disasters: list[str] | None = None
