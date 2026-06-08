from fastapi import APIRouter, Cookie

from src.shared.session import session_store
from src.summary import service
from src.summary.schemas import SummaryRequest, SummaryResponse

router = APIRouter()


@router.post("/v2/products/summary", response_model=SummaryResponse)
async def generate_summary(payload: SummaryRequest, session_id: str = Cookie(None)):
    # Get user API key and model from session if it exists
    api_key = None
    model_name = None
    if session_id:
        session_data = session_store.get_session(session_id)
        if session_data:
            api_key = session_data.get("api_key")
            model_name = session_data.get("selected_model")

    agg_input = service.combine_all_metadata_into_input(
        payload.ranked_sentences,
        payload.themes_detected,
        payload.top_locations,
        payload.top_locations,  # Using this as a placeholder for disasters if they are combined differently
    )
    summary = service.recursive_summarize(agg_input, api_key=api_key, model_name=model_name)
    return {"summary": summary, "status": "success"}
