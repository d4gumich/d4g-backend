from fastapi import APIRouter

from src.owl.schemas import OwlQuery, OwlResponse
from src.owl.service import owl_service

router = APIRouter()


@router.post("/v1/products/owl", response_model=OwlResponse)
async def ask_owl(payload: OwlQuery):
    return owl_service.ask_owl(
        text=payload.text,
        k=payload.k,
        gemini_model=payload.gemini_model,
        temperature=payload.temperature,
        max_docs=payload.max_docs,
    )
