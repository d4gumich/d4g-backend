from pydantic import BaseModel
from typing import Optional, List, Any

class LighthouseTextRequest(BaseModel):
    resume_text: str
    sanitize: bool = False

class LighthouseStatusResponse(BaseModel):
    stage: str
    hardware: str
    message: Optional[str] = None
    error: Optional[str] = None

class LighthouseAnalysisResponse(BaseModel):
    extracted_skills: Optional[Any] = None
    top_jobs: Optional[Any] = None
    recommendations: Optional[Any] = None
    status: str
    error: Optional[str] = None

class LighthousePDFResponse(BaseModel):
    status: str
    extracted_text: str
    length: int
    error: Optional[str] = None
