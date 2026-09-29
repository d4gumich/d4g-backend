from fastapi import APIRouter, Cookie, File, Form, HTTPException, Request, UploadFile

from src.hangul import service
from src.hangul.schemas import HangulDetectionResponse
from src.shared.byok import force_team, resolve_byok

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
        # Convert string "true"/"false" to actual booleans for the service
        # Normalize keys to lowercase for robustness
        instruct_dict = {k.lower(): str(v).lower() == "true" for k, v in form_data.items()}
        instruct_dict.pop("my_api_key", None)
        instruct_dict.pop("api_key", None)

        creds = resolve_byok(session_id, force_team=force_team(request))
        api_key = creds.api_key
        model_name = creds.model
        del my_API_key

        file_content = await file.read()
        results = service.detect_v2(file_content, kw_num, api_key, instruct_dict, model_name=model_name)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
