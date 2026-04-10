from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from src.lighthouse.schemas import (
    LighthouseTextRequest, 
    LighthouseStatusResponse, 
    LighthouseAnalysisResponse,
    LighthousePDFResponse
)
from src.lighthouse.service import lighthouse_service

router = APIRouter()

@router.post("/v1/products/lighthouse/wakeup", response_model=LighthouseStatusResponse)
async def wakeup_lighthouse():
    return lighthouse_service.wake_up()

@router.get("/v1/products/lighthouse/status", response_model=LighthouseStatusResponse)
async def get_lighthouse_status():
    return lighthouse_service.get_status()

@router.post("/v1/products/lighthouse/analyze-text", response_model=LighthouseAnalysisResponse)
async def analyze_text(payload: LighthouseTextRequest):
    return lighthouse_service.analyze(payload.resume_text, sanitize=payload.sanitize)

@router.post("/v1/products/lighthouse/parse-pdf", response_model=LighthousePDFResponse)
async def parse_pdf(
    file: UploadFile = File(...),
    sanitize: bool = Form(False)
):
    try:
        content = await file.read()
        extracted_text = lighthouse_service.parse_pdf(content, sanitize=sanitize)
        return {
            "status": "success",
            "extracted_text": extracted_text,
            "length": len(extracted_text)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
