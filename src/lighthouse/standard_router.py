import logging

from fastapi import APIRouter, Cookie, File, Form, HTTPException, UploadFile

from src.core.settings import settings
from src.lighthouse.schemas import LighthouseAnalysisResponse, LighthousePDFResponse, LighthouseTextRequest
from src.lighthouse.standard import (
    GeminiRejectedError,
    QdrantUnavailableError,
    default_embed,
    gemini_complete,
    query_configured_collection,
    run_standard_pipeline,
)
from src.shared.byok import resolve_byok

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_RESUME_CHARS = 50_000
MAX_PDF_BYTES = 5_000_000


def _require_gemini_session(session_id: str | None):
    creds = resolve_byok(session_id, force_team=False)
    if not creds.personal or not creds.api_key:
        raise HTTPException(status_code=401, detail="A personal API key session is required.")
    provider = (creds.provider or "").lower()
    if "google" not in provider and "gemini" not in provider:
        raise HTTPException(status_code=400, detail="Lighthouse standard mode requires a Gemini key.")
    return creds


@router.post("/v1/products/lighthouse/standard/analyze", response_model=LighthouseAnalysisResponse)
async def analyze_standard(payload: LighthouseTextRequest, session_id: str | None = Cookie(None)):
    creds = _require_gemini_session(session_id)
    resume = payload.resume_text or ""
    if len(resume) > MAX_RESUME_CHARS:
        raise HTTPException(status_code=413, detail="Resume text is too long.")

    async def complete(prompt: str) -> str:
        return await gemini_complete(prompt, creds.api_key or "", creds.model or settings.SOCRATES_STANDARD_MODEL)

    try:
        return await run_standard_pipeline(
            resume,
            complete=complete,
            embed=default_embed,
            query_points=query_configured_collection,
        )
    except QdrantUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except GeminiRejectedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None


@router.post("/v1/products/lighthouse/standard/parse-pdf", response_model=LighthousePDFResponse)
async def parse_standard_pdf(
    file: UploadFile = File(...),
    sanitize: bool = Form(False),
    session_id: str | None = Cookie(None),
):
    _require_gemini_session(session_id)
    content = await file.read()
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF is too large.")
    from src.lighthouse.service import lighthouse_service

    try:
        extracted = lighthouse_service.parse_pdf(content, sanitize=sanitize)
    except HTTPException:
        raise
    except Exception:
        logger.warning("Standard PDF parse failed")
        raise HTTPException(status_code=400, detail="The PDF could not be read.") from None
    return {"status": "success", "extracted_text": extracted, "length": len(extracted)}
