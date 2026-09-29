import hashlib
import secrets
import time
from dataclasses import dataclass

from fastapi import Request

from src.core.settings import settings
from src.shared.session import session_store

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
LOGOUT_PATH = "/api/v1/auth/logout"


@dataclass(frozen=True)
class ByokCredentials:
    api_key: str | None
    provider: str | None
    model: str | None
    personal: bool
    key_source: str


def tokens_match(provided: str | None, expected: str | None) -> bool:
    if not provided or not expected:
        return False
    return secrets.compare_digest(
        hashlib.sha256(provided.encode()).digest(),
        hashlib.sha256(expected.encode()).digest(),
    )


def redact_secret(text: str, secret: str | None) -> str:
    if not text:
        return ""
    if secret and secret in text:
        return text.replace(secret, "[redacted]")
    return text


def resolve_byok(session_id: str | None, force_team: bool = False) -> ByokCredentials:
    if not session_id:
        return ByokCredentials(None, None, None, False, "none")
    data = session_store.get_session(session_id)
    if not data or data.get("is_lighthouse"):
        return ByokCredentials(None, None, None, False, "none")
    has_key = isinstance(data.get("api_key"), str) and bool(data.get("api_key"))
    provider = data.get("provider")
    model = data.get("selected_model")
    if force_team or not has_key:
        return ByokCredentials(None, provider, model, False, "team")
    return ByokCredentials(data.get("api_key"), provider, model, True, "personal")


def force_team(request: Request) -> bool:
    return request.headers.get("x-force-team-key", "").lower() == "true"


def csrf_rejected(
    method: str,
    path: str,
    session_cookie: str | None,
    lighthouse_cookie: str | None,
    session_header: str | None,
    lighthouse_header: str | None,
) -> bool:
    if method.upper() in SAFE_METHODS or path == LOGOUT_PATH:
        return False
    session_csrf = session_store.peek_csrf(session_cookie) if session_cookie else None
    if session_csrf and not tokens_match(session_header, session_csrf):
        return True
    lighthouse_csrf = session_store.peek_csrf(lighthouse_cookie) if lighthouse_cookie else None
    if lighthouse_csrf and not tokens_match(lighthouse_header, lighthouse_csrf):
        return True
    return False


def origin_rejected(method: str, origin: str | None, allowed: list[str], own_origin: str) -> bool:
    if method.upper() in SAFE_METHODS or not origin or not allowed:
        return False
    return origin not in allowed and origin != own_origin


def client_ip(request: Request) -> str:
    if settings.PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[-1].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class AttemptLimiter:
    def __init__(self, limit: int = 30, window: int = 600, clock=time.time):
        self.limit = limit
        self.window = window
        self.clock = clock
        self.hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = self.clock()
        recent = [stamp for stamp in self.hits.get(key, []) if now - stamp < self.window]
        if len(recent) >= self.limit:
            self.hits[key] = recent
            return False
        recent.append(now)
        self.hits[key] = recent
        return True


auth_attempts = AttemptLimiter()
