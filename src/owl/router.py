from fastapi import APIRouter, Cookie

from src.owl.schemas import OwlQuery, OwlResponse
from src.owl.service import owl_service
from src.shared.session import session_store

router = APIRouter()


@router.post("/v1/products/owl", response_model=OwlResponse)
async def ask_owl(payload: OwlQuery, session_id: str = Cookie(None)):
    # Get user API key and model from session if it exists
    api_key = None
    session_model = None
    if session_id:
        session_data = session_store.get_session(session_id)
        if session_data:
            api_key = session_data.get("api_key")
            session_model = session_data.get("selected_model")

    return owl_service.ask_owl(
        text=payload.text,
        k=payload.k,
        gemini_model=payload.gemini_model or session_model,
        temperature=payload.temperature,
        max_docs=payload.max_docs,
        api_key=api_key,
    )
