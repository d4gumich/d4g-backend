import secrets
from datetime import datetime as _datetime
from datetime import timezone

# Tests replace this name so they can freeze schedule_router.datetime.now
# without losing datetime.fromisoformat.
datetime = _datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Cookie, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from src.core.settings import settings
from src.lighthouse.dev_schedule import (
    apply_dev_schedule,
    clear_dev_seats,
    dev_preset,
    dev_window,
    fill_dev_seats,
    set_dev_preset,
)
from src.lighthouse.engine_status import engine_snapshot
from src.lighthouse.reconcile import run_tick
from src.lighthouse.schedule import build_schedule_payload, load_schedule
from src.lighthouse.seats import SEAT_CAP, claim_seat, holds_seat, seat_count
from src.lighthouse.service import lighthouse_service
from src.shared.session import session_store

router = APIRouter()
DETROIT = ZoneInfo("America/Detroit")


def _token_matches(provided: str | None, expected: str) -> bool:
    if not provided or len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided, expected)


class SeatClaim(BaseModel):
    token: str
    session: str


class DevCommand(BaseModel):
    preset: str
    session: str | None = None


class SeatAnalysis(BaseModel):
    token: str
    session: str
    resume_text: str
    sanitize: bool = False


_UPLOAD_PHASES = frozenset({"pre_warm", "open", "drain"})
_ANALYZE_PHASES = frozenset({"open", "drain"})


def require_scheduled_tester(
    x_experimental_api_key: str | None = Header(None),
    lighthouse_session: str | None = Cookie(None),
) -> None:
    """A scheduled seat is the user test, so it needs the team key or that session."""
    if lighthouse_session:
        session_data = session_store.get_session(lighthouse_session)
        if session_data and session_data.get("is_lighthouse"):
            return
    expected = settings.EXPERIMENTAL_ACCESS_KEY
    if expected and x_experimental_api_key == expected:
        return
    raise HTTPException(
        status_code=403,
        detail="A team security key is required for this user test.",
    )


def _seat_window(token: str, session: str, phases: frozenset[str]) -> dict:
    if not holds_seat(token, session):
        raise HTTPException(status_code=403, detail="A saved seat is required.")
    payload = _public_payload(datetime.now(timezone.utc))
    if payload.get("phase") not in phases or payload.get("seat_session") != session:
        detail = (
            "Analysis opens when the session is live and the engine is ready."
            if phases is _ANALYZE_PHASES
            else "Resume upload is closed for this session."
        )
        raise HTTPException(status_code=409, detail=detail)
    return payload


def _schedule_for_visitors():
    schedule = load_schedule()
    if settings.LIGHTHOUSE_DEV_SCHEDULE:
        return apply_dev_schedule(schedule)
    return schedule


def _public_payload(now: datetime) -> dict:
    payload = _with_seats(build_schedule_payload(_schedule_for_visitors(), now))
    if settings.LIGHTHOUSE_DEV_SCHEDULE:
        window = dev_window()
        payload["dev"] = True
        payload["dev_preset"] = dev_preset()
        payload["dev_date"] = window.date if window else None
    return payload


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
    return _public_payload(datetime.now(timezone.utc))


@router.get("/v1/products/lighthouse/schedule/engine")
async def get_schedule_engine():
    payload = _public_payload(datetime.now(timezone.utc))
    return engine_snapshot(
        payload["phase"],
        bool(payload.get("dev_preset")),
        lighthouse_service.get_status,
    )


@router.post("/v1/products/lighthouse/schedule/parse")
async def parse_for_seat(
    token: str = Form(...),
    session: str = Form(...),
    sanitize: bool = Form(False),
    file: UploadFile = File(...),
    _: None = Depends(require_scheduled_tester),
):
    _seat_window(token, session, _UPLOAD_PHASES)
    content = await file.read()
    extracted = lighthouse_service.parse_pdf(content, sanitize=sanitize)
    return {"status": "success", "extracted_text": extracted, "length": len(extracted)}


@router.post("/v1/products/lighthouse/schedule/analyze")
async def analyze_for_seat(body: SeatAnalysis, _: None = Depends(require_scheduled_tester)):
    payload = _seat_window(body.token, body.session, _ANALYZE_PHASES)
    if payload.get("dev_preset"):
        raise HTTPException(status_code=409, detail="This practice session does not start the engine.")
    status = lighthouse_service.get_status()
    if (status.get("stage") or "").upper() != "RUNNING":
        raise HTTPException(status_code=409, detail="The engine is still starting.")
    return lighthouse_service.analyze(body.resume_text, sanitize=body.sanitize)


@router.post("/v1/products/lighthouse/schedule/dev")
async def configure_dev_schedule(body: DevCommand):
    if not settings.LIGHTHOUSE_DEV_SCHEDULE:
        raise HTTPException(status_code=404, detail="Not found.")
    now = datetime.now(timezone.utc)
    try:
        if body.preset == "reset_seats":
            clear_dev_seats()
        elif body.preset == "fill_seats":
            if not body.session:
                raise ValueError("missing session")
            fill_dev_seats(body.session)
        else:
            set_dev_preset(body.preset, now)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid dev schedule request.") from exc
    return _public_payload(now)


@router.post("/v1/products/lighthouse/schedule/seats")
async def claim_schedule_seat(body: SeatClaim, _: None = Depends(require_scheduled_tester)):
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
    # Practice sessions stay off this path so a dev window cannot wake the GPU.
    result = run_tick(lighthouse_service, load_schedule(), datetime.now(timezone.utc))
    if result["action"] == "error":
        raise HTTPException(status_code=502, detail=result.get("detail") or "Tick failed")
    return result
