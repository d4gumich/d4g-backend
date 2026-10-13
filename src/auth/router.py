import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, HTTPException, Request, Response

from src.auth.schemas import ModelsRequest, ModelsResponse, SessionCreate, SessionResponse
from src.core.settings import settings
from src.shared.byok import auth_attempts, client_ip, redact_secret, tokens_match
from src.shared.llm_factory import fetch_available_models, validate_key
from src.shared.session import SessionCapacityError, session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/auth", tags=["auth"])

PERSONAL_TTL = 1800
LIGHTHOUSE_TTL = 3540


def _stamp(response: Response, key: str, value: str, max_age: int) -> None:
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="none",
        path="/",
    )


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def refresh_session_cookies(request: Request, response: Response) -> None:
    """Keep the browser cookie aligned with the sliding idle deadline."""
    already_set = {header.split("=", 1)[0].strip() for header in response.headers.getlist("set-cookie")}
    pairs = (
        ("session_id", request.cookies.get("session_id")),
        ("lighthouse_session", request.cookies.get("lighthouse_session")),
    )
    for name, value in pairs:
        if not value or name in already_set:
            continue
        if session_store.get_session(value) is None:
            continue
        deadlines = session_store.deadlines(value)
        if deadlines is None:
            continue
        remaining = int(deadlines[0] - time.time())
        if remaining < 1:
            continue
        _stamp(response, name, value, remaining)


def _clear(response: Response, key: str) -> None:
    response.set_cookie(
        key=key,
        value="",
        max_age=0,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="none",
        path="/",
    )


def _guard_attempts(request: Request) -> None:
    if not auth_attempts.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many session attempts. Try again later.")


def _session_body(session_id: str) -> dict[str, str]:
    token = session_store.peek_csrf(session_id)
    if not token:
        raise HTTPException(status_code=500, detail="Session could not be started.")
    return {"status": "success", "csrf_token": token}


@router.post("/models", response_model=ModelsResponse)
async def get_available_models(payload: ModelsRequest, request: Request):
    _guard_attempts(request)
    try:
        models = await fetch_available_models(payload.provider, payload.api_key)
        return {"models": models, "status": "success"}
    except Exception as exc:
        error_msg = redact_secret(str(exc), payload.api_key).lower()
        logger.warning("Model lookup failed: %s", redact_secret(str(exc), payload.api_key))
        if "401" in error_msg or "403" in error_msg or "api_key_invalid" in error_msg:
            raise HTTPException(status_code=401, detail="API key was rejected.") from None
        raise HTTPException(status_code=500, detail="Model lookup failed.") from None


@router.post("/session", response_model=SessionResponse)
async def initialize_session(
    payload: SessionCreate, request: Request, response: Response, session_id: str | None = Cookie(None)
):
    _guard_attempts(request)
    if not payload.api_key:
        if session_id and session_store.get_session(session_id):
            session_store.update_session(session_id, {"provider": payload.provider, "selected_model": payload.model})
            return _session_body(session_id)

        try:
            new_session_id = session_store.create_session(
                {"provider": payload.provider, "selected_model": payload.model, "api_key": None}
            )
        except SessionCapacityError as exc:
            raise HTTPException(status_code=503, detail="Session capacity is full. Try again later.") from exc
        _stamp(response, "session_id", new_session_id, PERSONAL_TTL)
        return _session_body(new_session_id)

    is_valid, error_detail = await validate_key(payload.provider, payload.model, payload.api_key)
    if not is_valid:
        logger.warning("API key validation failed: %s", redact_secret(error_detail, payload.api_key))
        raise HTTPException(status_code=401, detail="API key was rejected.")

    if session_id:
        session_store.delete_session(session_id)

    try:
        new_session_id = session_store.create_session(
            {"provider": payload.provider, "selected_model": payload.model, "api_key": payload.api_key}
        )
    except SessionCapacityError as exc:
        raise HTTPException(status_code=503, detail="Session capacity is full. Try again later.") from exc
    _stamp(response, "session_id", new_session_id, PERSONAL_TTL)
    return _session_body(new_session_id)


@router.post("/lighthouse-session", response_model=SessionResponse)
async def initialize_lighthouse_session(
    payload: SessionCreate, request: Request, response: Response, lighthouse_session: str | None = Cookie(None)
):
    _guard_attempts(request)
    if not tokens_match(payload.api_key, settings.EXPERIMENTAL_ACCESS_KEY):
        raise HTTPException(status_code=401, detail="Invalid team security key.")

    if lighthouse_session:
        session_store.delete_session(lighthouse_session)

    try:
        new_session_id = session_store.create_session(
            {"is_lighthouse": True, "provider": payload.provider, "selected_model": payload.model},
            ttl=LIGHTHOUSE_TTL,
        )
    except SessionCapacityError as exc:
        raise HTTPException(status_code=503, detail="Session capacity is full. Try again later.") from exc
    _stamp(response, "lighthouse_session", new_session_id, LIGHTHOUSE_TTL)
    return _session_body(new_session_id)


@router.get("/lighthouse-status")
async def get_lighthouse_session_status(lighthouse_session: str | None = Cookie(None)):
    if lighthouse_session:
        session_data = session_store.get_session(lighthouse_session)
        if session_data and session_data.get("is_lighthouse"):
            return {"status": "active", "csrf_token": session_data.get("csrf_token")}
    return {"status": "inactive"}


@router.get("/status")
async def get_session_status(session_id: str | None = Cookie(None)):
    if session_id:
        session_data = session_store.get_session(session_id)
        if session_data and not session_data.get("is_lighthouse"):
            key_source = "personal" if session_data.get("api_key") else "team"
            deadlines = session_store.deadlines(session_id)
            idle_at, absolute_at = deadlines if deadlines else (None, None)
            return {
                "status": "active",
                "provider": session_data.get("provider"),
                "model": session_data.get("selected_model"),
                "key_source": key_source,
                "csrf_token": session_data.get("csrf_token"),
                "expires_at": _iso(idle_at) if idle_at is not None else None,
                "absolute_expires_at": _iso(absolute_at) if absolute_at is not None else None,
            }
    return {"status": "inactive", "key_source": "none"}


@router.post("/logout")
async def logout(
    response: Response,
    session_id: str | None = Cookie(None),
    lighthouse_session: str | None = Cookie(None),
):
    if session_id:
        session_store.delete_session(session_id)
    if lighthouse_session:
        session_store.delete_session(lighthouse_session)
    _clear(response, "session_id")
    _clear(response, "lighthouse_session")
    return {"status": "success"}
