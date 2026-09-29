import secrets
from datetime import datetime as _datetime
from datetime import timezone

# Tests replace this name so they can freeze schedule_router.datetime.now
# without losing datetime.fromisoformat.
datetime = _datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.core.settings import settings
from src.lighthouse.reconcile import run_tick
from src.lighthouse.schedule import build_schedule_payload, load_schedule
from src.lighthouse.seats import SEAT_CAP, claim_seat, seat_count
from src.lighthouse.service import lighthouse_service

router = APIRouter()
DETROIT = ZoneInfo("America/Detroit")


def _token_matches(provided: str | None, expected: str) -> bool:
    if not provided or len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided, expected)


class SeatClaim(BaseModel):
    token: str
    session: str


def _session_id(window: dict | None) -> str | None:
    if not window or not window.get("start"):
        return None
    start = _datetime.fromisoformat(window["start"]).astimezone(DETROIT)
    return start.date().isoformat()


def _with_seats(payload: dict) -> dict:
    counts: dict[str, int] = {}
    for window in payload.get("upcoming") or []:
        session_id = _session_id(window)
        if session_id:
            counts[session_id] = seat_count(session_id)
    focus = _session_id(payload.get("current_window")) or _session_id((payload.get("upcoming") or [None])[0])
    if focus and focus not in counts:
        counts[focus] = seat_count(focus)
    payload["seat_cap"] = SEAT_CAP
    payload["seat_session"] = focus
    payload["seats_taken"] = counts.get(focus, 0) if focus else 0
    payload["seats"] = counts
    return payload


@router.get("/v1/products/lighthouse/schedule")
async def get_schedule():
    schedule = load_schedule()
    payload = build_schedule_payload(schedule, datetime.now(timezone.utc))
    return _with_seats(payload)


@router.post("/v1/products/lighthouse/schedule/seats")
async def claim_schedule_seat(body: SeatClaim):
    try:
        return claim_seat(body.token, body.session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid seat request.") from exc


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
