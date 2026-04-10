from fastapi import APIRouter

from src.summary import service
from src.summary.schemas import SummaryRequest, SummaryResponse

router = APIRouter()


@router.post("/v2/products/summary", response_model=SummaryResponse)
async def generate_summary(payload: SummaryRequest):
    agg_input = service.combine_all_metadata_into_input(
        payload.ranked_sentences,
        payload.themes_detected,
        payload.top_locations,
        payload.top_locations,  # Using this as a placeholder for disasters if they are combined differently
    )
    summary = service.recursive_summarize(agg_input)
    return {"summary": summary, "status": "success"}
