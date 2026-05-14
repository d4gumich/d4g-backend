from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from src.hangul import service
from src.hangul.schemas import HangulDetectionResponse

router = APIRouter()


@router.post("/v1/products/hangul", response_model=HangulDetectionResponse)
async def hangul_v1(file: UploadFile = File(...), kw_num: int = Form(...)):
    try:
        file_content = await file.read()
        results = service.detect_v1(file_content, file.filename or "unknown.pdf", kw_num)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v2/products/hangul", response_model=HangulDetectionResponse)
async def hangul_v2(
    request: Request, file: UploadFile = File(...), kw_num: int = Form(...), my_API_key: str | None = Form(None)
):
    try:
        # Get all form data as a dict for instruct_dict
        form_data = await request.form()
        instruct_dict = dict(form_data)

        file_content = await file.read()
        results = service.detect_v2(file_content, kw_num, my_API_key, instruct_dict)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
