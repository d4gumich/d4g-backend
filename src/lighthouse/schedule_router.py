import secrets
from datetime import datetime as _datetime
from datetime import timedelta, timezone

# Tests replace this name so they can freeze schedule_router.datetime.now
# without losing datetime.fromisoformat.
datetime = _datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Cookie, Depends, File, Form, Header, HTTPException, Response, UploadFile
from pydantic import BaseModel

from src.core.settings import settings
from src.lighthouse.dev_schedule import (
    apply_dev_schedule,
    clear_dev_seats,
    dev_forwarded,
    dev_open_started,
    dev_preset,
    dev_window,
    fast_forward_dev_window,
    fill_dev_seats,
    set_dev_preset,
    start_open_clock,
)
from src.lighthouse.engine_status import (
    begin_startup_timer,
    clear_startup_timer,
    engine_snapshot,
    gpu_test_armed,
    mark_gpu_test_armed,
    reset_engine_status,
    startup_report,
    step_for,
)
from src.lighthouse.reconcile import decide, run_tick
from src.lighthouse.schedule import build_schedule_payload, load_schedule
from src.lighthouse.seats import SEAT_CAP, claim_seat, holds_seat, release_seat, seat_count
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
_PRACTICE_PRESETS = frozenset({"soon", "open", "drain", "ended"})
_ENDED_DETAIL = "This session has ended."
_DRAIN_DETAIL = "No more new seats. People who already have a seat are finishing before the server shuts down."
_KEEP_SEAT_DETAIL = "This seat stays until the session is finished."
_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


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
        preset = dev_preset()
        payload["dev"] = True
        payload["dev_preset"] = preset
        payload["dev_date"] = window.date if window else None
        # An ended practice window is not "upcoming", so its count has to be added
        # or the calendar shows 0 and Take a seat stays active.
        if window is not None and preset in _PRACTICE_PRESETS:
            payload["seats"][window.date] = seat_count(window.date)
            payload["seat_session"] = window.date
            payload["seats_taken"] = payload["seats"][window.date]
        payload["dev_forwarded"] = dev_forwarded()
        waiting = preset == "open" and not dev_open_started()
        payload["dev_waiting_for_seat"] = waiting
        # The Open now clock starts with the first seat, together with the GPU.
        if waiting:
            payload["phase"] = "closed"
            payload["countdown_to"] = None
            payload["current_window"] = None
    return payload


def _clock_on(day: str, hhmm: str) -> _datetime:
    hour, minute = (int(part) for part in hhmm.split(":"))
    year, month, date = (int(part) for part in day.split("-"))
    return _datetime(year, month, date, hour, minute, tzinfo=DETROIT)


def _window_bounds(payload: dict, session: str) -> tuple[_datetime, _datetime] | None:
    for item in payload.get("one_off") or []:
        if item.get("date") == session and item.get("start") and item.get("end"):
            return _clock_on(session, item["start"]), _clock_on(session, item["end"])
    try:
        day = _datetime.fromisoformat(session)
    except ValueError:
        return None
    weekday = _WEEKDAY_NAMES[day.weekday()]
    for item in payload.get("weekly") or []:
        if item.get("weekday") == weekday and item.get("start") and item.get("end"):
            return _clock_on(session, item["start"]), _clock_on(session, item["end"])
    return None


def _new_seat_block(payload: dict, session: str, now: _datetime) -> str | None:
    if payload.get("dev_waiting_for_seat"):
        return None
    bounds = _window_bounds(payload, session)
    if bounds is None:
        return None
    _start, end = bounds
    moment = now.astimezone(DETROIT)
    if moment >= end:
        return _ENDED_DETAIL
    drain_minutes = int(payload.get("drain_minutes") or 0)
    if moment >= end - timedelta(minutes=drain_minutes):
        return _DRAIN_DETAIL
    return None


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
async def get_schedule(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return _public_payload(datetime.now(timezone.utc))


@router.get("/v1/products/lighthouse/schedule/engine")
async def get_schedule_engine():
    payload = _public_payload(datetime.now(timezone.utc))
    # Open now is the one practice preset that reads Hugging Face, so its timer can finish.
    practice = bool(payload.get("dev_preset")) and payload.get("dev_preset") != "open"
    snapshot = engine_snapshot(payload["phase"], practice, lighthouse_service.get_status)
    if payload.get("dev_waiting_for_seat"):
        snapshot["summary"] = "The engine is off. It starts when someone takes a seat."
    return snapshot


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
    preset = payload.get("dev_preset")
    if preset and preset != "open":
        raise HTTPException(status_code=409, detail="This practice session does not start the engine.")
    status = lighthouse_service.get_status()
    if (status.get("stage") or "").upper() != "RUNNING":
        raise HTTPException(status_code=409, detail="The engine is still starting.")
    return lighthouse_service.analyze(body.resume_text, sanitize=body.sanitize)


_LIVE_PHASES = frozenset({"pre_warm", "open", "drain"})


def _can_start_engine(now: datetime) -> bool:
    """The GPU stays off until someone has a seat and the session is still starting or open."""
    payload = _public_payload(now)
    if payload.get("phase") not in {"pre_warm", "open"}:
        return False
    session = payload.get("seat_session") or payload.get("dev_date")
    if not isinstance(session, str) or not session:
        return False
    return seat_count(session) >= 1


def _arm_open_gpu(now: datetime) -> None:
    """Open now is the explicit GPU test. The scheduler tick still ignores practice windows."""
    if gpu_test_armed() or startup_report(now) is not None:
        return
    if not _can_start_engine(now):
        return
    before = lighthouse_service.get_status()
    stage = (before.get("stage") or "").upper()
    if decide("open", stage, before.get("hardware")) == "wake":
        lighthouse_service.wake_up()
        mark_gpu_test_armed()
        begin_startup_timer(now)
    elif stage == "RUNNING":
        begin_startup_timer(now, ready_at=now)
    else:
        begin_startup_timer(now, initial_step=step_for(stage))
    reset_engine_status()


def _maybe_start_engine(now: datetime) -> None:
    """Start only after a seat exists. Practice modes other than Open now stay off the GPU."""
    payload = _public_payload(now)
    preset = payload.get("dev_preset")
    if preset == "open":
        _arm_open_gpu(now)
        return
    if preset or not _can_start_engine(now):
        return
    status = lighthouse_service.get_status()
    action = decide(
        payload["phase"],
        status.get("stage"),
        status.get("hardware"),
        payload.get("hardware") or "t4-medium",
        occupied=True,
    )
    if action == "wake":
        lighthouse_service.wake_up()


def _release_open_gpu(now: datetime) -> None:
    armed = gpu_test_armed()
    clear_startup_timer()
    reset_engine_status()
    if not armed:
        return
    real = build_schedule_payload(load_schedule(), now)
    if real.get("phase") in _LIVE_PHASES:
        return
    lighthouse_service.stop_space()


@router.post("/v1/products/lighthouse/schedule/dev")
async def configure_dev_schedule(body: DevCommand):
    if not settings.LIGHTHOUSE_DEV_SCHEDULE:
        raise HTTPException(status_code=404, detail="Not found.")
    now = datetime.now(timezone.utc)
    previous = dev_preset()
    try:
        if body.preset == "reset_seats":
            clear_dev_seats()
        elif body.preset == "fill_seats":
            if not body.session:
                raise ValueError("missing session")
            fill_dev_seats(body.session)
        elif body.preset == "fast_forward":
            fast_forward_dev_window(now)
        else:
            set_dev_preset(body.preset, now)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid dev schedule request.") from exc
    if previous == "open" and body.preset not in {"open", "reset_seats", "fill_seats", "fast_forward"}:
        _release_open_gpu(now)
    if body.preset == "open" or (body.preset == "fill_seats" and dev_preset() == "open"):
        start_open_clock(now)
        _arm_open_gpu(now)
    return _public_payload(now)


@router.post("/v1/products/lighthouse/schedule/seats")
async def claim_schedule_seat(body: SeatClaim, _: None = Depends(require_scheduled_tester)):
    now = datetime.now(timezone.utc)
    try:
        if holds_seat(body.token, body.session):
            return claim_seat(body.token, body.session)
        block = _new_seat_block(_public_payload(now), body.session, now)
        if block:
            raise HTTPException(status_code=409, detail=block)
        claimed = claim_seat(body.token, body.session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid seat request.") from exc
    if claimed.get("accepted"):
        start_open_clock(now)
        _maybe_start_engine(now)
    return claimed


@router.post("/v1/products/lighthouse/schedule/seats/release")
async def release_schedule_seat(body: SeatClaim, _: None = Depends(require_scheduled_tester)):
    now = datetime.now(timezone.utc)
    if holds_seat(body.token, body.session):
        block = _new_seat_block(_public_payload(now), body.session, now)
        if block == _DRAIN_DETAIL:
            raise HTTPException(status_code=409, detail=_KEEP_SEAT_DETAIL)
        if block:
            raise HTTPException(status_code=409, detail=block)
    try:
        return release_seat(body.token, body.session)
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
