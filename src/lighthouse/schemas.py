from typing import Any

from pydantic import BaseModel


class LighthouseTextRequest(BaseModel):
    resume_text: str
    sanitize: bool = False


class LighthouseStatusResponse(BaseModel):
    stage: str
    hardware: str
    message: str | None = None
    error: str | None = None


class LighthouseAnalysisResponse(BaseModel):
    extracted_skills: Any | None = None
    top_jobs: Any | None = None
    recommendations: Any | None = None
    status: str
    error: str | None = None


class LighthousePDFResponse(BaseModel):
    status: str
    extracted_text: str
    length: int
    error: str | None = None
