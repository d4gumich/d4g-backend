import json
import logging
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.socrates.schemas import SocratesRequest, SocratesState
from src.socrates.service import socrates_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/products/socrates", tags=["socrates"])


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
        try:
            # event is a dict: {node_name: {state_updates}}
            config = {"configurable": {"thread_id": session_id}}
            async for event in socrates_service.graph.astream(initial_state, config):
                # SSE formatting: data: {json}\n\n
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Socrates stream error: {e}")
            # Yield an error event so the frontend can catch it and retry
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/resume/{session_id}")
async def resume_socrates(session_id: str):
    """
    Resumes the Socrates process from a pause.
    Uses the thread_id to continue from the last checkpoint.
    """

    async def event_generator():
        try:
            config = {"configurable": {"thread_id": session_id}}
            # Pass None as initial state to continue from the last checkpoint
            async for event in socrates_service.graph.astream(None, config):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Socrates resume stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
