from fastapi import APIRouter, Cookie, Request

from src.owl.schemas import OwlQuery, OwlResponse
from src.owl.service import owl_service
from src.shared.byok import force_team, resolve_byok

router = APIRouter()


@router.post("/v1/products/owl", response_model=OwlResponse)
async def ask_owl(payload: OwlQuery, request: Request, session_id: str | None = Cookie(None)):
    creds = resolve_byok(session_id, force_team=force_team(request))
    return await owl_service.ask_owl(
        text=payload.text,
        k=payload.k,
        gemini_model=payload.gemini_model or creds.model,
        temperature=payload.temperature,
        max_docs=payload.max_docs,
        api_key=creds.api_key,
    )
