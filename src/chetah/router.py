from fastapi import APIRouter
from src.chetah.schemas import ChetahQuery, ChetahResponse, ChetahResult
from src.chetah import service

router = APIRouter()

@router.post("/v1/products/chetah", response_model=ChetahResponse)
async def chetah_v1(payload: ChetahQuery):
    results = service.search_v1(payload.query)
    return {"results": results}

@router.post("/v2/products/chetah", response_model=ChetahResponse)
async def chetah_v2(payload: ChetahQuery):
    results = service.search_v2(payload.query)
    # v2 returns slightly different field names in doc_dict, we need to map them if they don't match ChetahResult
    # Actually, ChetahResult is flexible. Let's ensure compatibility.
    return {"results": results}
