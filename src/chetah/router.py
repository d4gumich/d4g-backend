from fastapi import APIRouter

from src.chetah import service
from src.chetah.schemas import ChetahQuery, ChetahResponse

router = APIRouter()


@router.post("/v1/products/chetah", response_model=ChetahResponse)
async def chetah_v1(payload: ChetahQuery):
    results = service.search_v1(payload.query)
    return {"results": results}


@router.post("/v2/products/chetah", response_model=ChetahResponse)
async def chetah_v2(payload: ChetahQuery):
    results = service.search_v2(payload.query)
    mapped_results = []
    for r in results:
        mapped_results.append(
            {
                "title": str(r.get("report_title", ["Untitled"])[0]),
                "date": str(r.get("doc_creation_date", "")),
                "link": str(r.get("URL", "")),
                "cluster": str(r.get("organization_name", "")),  # Using org as cluster placeholder if not present
                "summary_short": str(r.get("summary", ""))[:450],
                "summary_full": str(r.get("summary", "")),
            }
        )
    return {"results": mapped_results}
