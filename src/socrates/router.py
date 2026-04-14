import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.socrates.schemas import SocratesRequest, SocratesState
from src.socrates.service import socrates_service

router = APIRouter(prefix="/v1/socrates", tags=["socrates"])


@router.post("/run")
async def run_socrates(request: SocratesRequest):
    """
    Runs the Socrates dialectic process and yields events as Server-Sent Events (SSE).
    """
    run_id = str(uuid.uuid4())
    session_id = request.session_id or str(uuid.uuid4())

    initial_state = SocratesState(
        raw_input=request.input,
        session_id=session_id,
        run_id=run_id,
        channel=request.channel,
    )

    async def event_generator():
        # event is a dict: {node_name: {state_updates}}
        async for event in socrates_service.graph.astream(initial_state):
            # SSE formatting: data: {json}\n\n
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/resume/{run_id}")
async def resume_socrates(run_id: str):
    """Placeholder for resuming from a pause."""
    return {"message": f"Resume endpoint for {run_id} (placeholder)"}
