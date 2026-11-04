from fastapi import APIRouter, Cookie, Request

from src.shared.byok import force_team, resolve_byok
from src.summary import service
from src.summary.schemas import SummaryRequest, SummaryResponse

router = APIRouter()


@router.post("/v2/products/summary", response_model=SummaryResponse)
async def generate_summary(payload: SummaryRequest, request: Request, session_id: str | None = Cookie(None)):
    creds = resolve_byok(session_id, force_team=force_team(request))
    api_key = creds.api_key
    model_name = creds.model

    agg_input = service.combine_all_metadata_into_input(
        payload.ranked_sentences,
        payload.themes_detected,
        payload.top_locations,
        payload.top_locations,  # Using this as a placeholder for disasters if they are combined differently
    )
    summary = service.recursive_summarize(agg_input, api_key=api_key, model_name=model_name)
    return {"summary": summary, "status": "success"}
