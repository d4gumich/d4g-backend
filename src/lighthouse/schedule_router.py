import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException

from src.core.settings import settings
from src.lighthouse.reconcile import run_tick
from src.lighthouse.schedule import build_schedule_payload, load_schedule
from src.lighthouse.service import lighthouse_service

router = APIRouter()


def _token_matches(provided: str | None, expected: str) -> bool:
    if not provided or len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided, expected)


@router.get("/v1/products/lighthouse/schedule")
async def get_schedule():
    schedule = load_schedule()
    return build_schedule_payload(schedule, datetime.now(timezone.utc))


@router.post("/v1/products/lighthouse/schedule/tick")
async def tick_schedule(x_scheduler_token: str | None = Header(None)):
    expected = settings.LIGHTHOUSE_SCHEDULER_TOKEN
    if not expected:
        raise HTTPException(status_code=503, detail="Scheduler token is not configured.")
    if not _token_matches(x_scheduler_token, expected):
        raise HTTPException(status_code=403, detail="Invalid scheduler token.")
    result = run_tick(lighthouse_service, load_schedule(), datetime.now(timezone.utc))
    if result["action"] == "error":
        raise HTTPException(status_code=502, detail=result.get("detail") or "Tick failed")
    return result
