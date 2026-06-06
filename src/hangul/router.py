from fastapi import APIRouter, Cookie, File, Form, HTTPException, Request, UploadFile

from src.hangul import service
from src.hangul.schemas import HangulDetectionResponse
from src.shared.session import session_store

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
    request: Request,
    file: UploadFile = File(...),
    kw_num: int = Form(...),
    my_API_key: str | None = Form(None),
    session_id: str = Cookie(None),
):
    try:
        # Get all form data as a dict for instruct_dict
        form_data = await request.form()
        instruct_dict = dict(form_data)

        # Priority: Direct API key form field > Session key from cookie
        api_key = my_API_key
        model_name = None
        if not api_key and session_id:
            session_data = session_store.get_session(session_id)
            if session_data:
                api_key = session_data.get("api_key")
                model_name = session_data.get("selected_model")

        file_content = await file.read()
        results = service.detect_v2(file_content, kw_num, api_key, instruct_dict, model_name=model_name)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
