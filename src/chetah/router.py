from fastapi import APIRouter

from src.chetah import service
from src.chetah.schemas import ChetahQuery, ChetahResult

router = APIRouter()


@router.get("/v1/products/chetah", response_model=list[ChetahResult])
async def chetah_v1_get(query: str):
    return service.search_v1(query)


@router.post("/v1/products/chetah", response_model=list[ChetahResult])
async def chetah_v1_post(payload: ChetahQuery):
    return service.search_v1(payload.query)


@router.get("/v2/products/chetah", response_model=list[ChetahResult])
async def chetah_v2_get(query: str):
    results = service.search_v2(query)
    return _map_v2_results(results)


@router.post("/v2/products/chetah", response_model=list[ChetahResult])
async def chetah_v2_post(payload: ChetahQuery):
    results = service.search_v2(payload.query)
    return _map_v2_results(results)


def _map_v2_results(results: list) -> list:
    mapped_results = []
    for r in results:
        # Robust title extraction for v1 compatibility
        title_list = r.get("report_title")
        v1_title = "Untitled"
        if title_list and isinstance(title_list, list) and len(title_list) > 0:
            v1_title = str(title_list[0]).strip() or "Untitled"
        elif isinstance(title_list, str):
            v1_title = title_list.strip() or "Untitled"

        # Create a combined dict that has both raw v2 fields and mapped v1 fields
        res_dict = dict(r)
        res_dict.update(
            {
                "title": v1_title,
                "date": str(r.get("doc_creation_date") or "").strip(),
                "link": str(r.get("URL") or "").strip(),
                "cluster": str(r.get("organization_name") or "").strip(),
                "summary_short": str(r.get("summary") or "")[:450],
                "summary_full": str(r.get("summary") or ""),
            }
        )
        mapped_results.append(res_dict)
    return mapped_results
