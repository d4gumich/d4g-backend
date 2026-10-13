import base64
import hashlib
import logging
import secrets
import time
from collections.abc import Callable
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from src.core.settings import settings

logger = logging.getLogger(__name__)


class SessionCapacityError(RuntimeError):
    pass


def master_fernet(secret: str | None) -> Fernet:
    """Build a Fernet handle from a dedicated session secret.

    An empty secret creates an ephemeral process key. Sessions then die on
    restart, and the Owl or Gemini API key is never reused as key material.
    """
    if not secret:
        return Fernet(Fernet.generate_key())
    digest = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


_cipher = master_fernet(getattr(settings, "SESSION_ENCRYPTION_KEY", None))


class SessionStore:
    def __init__(
        self,
        ttl: int = 1800,
        absolute_ttl: int = 12 * 3600,
        max_sessions: int = 10000,
        clock: Callable[[], float] | None = None,
        cipher: Fernet | None = None,
    ):
        self._sessions: dict[str, dict[str, Any]] = {}
        self._ttl = ttl
        self._absolute_ttl = absolute_ttl
        self._max_sessions = max_sessions
        self._clock = clock or time.time
        self._cipher = cipher or _cipher

    def create_session(self, data: dict[str, Any], ttl: int | None = None) -> str:
        self._cleanup()
        if len(self._sessions) >= self._max_sessions:
            raise SessionCapacityError("session store is full")

        session_id = secrets.token_urlsafe(32)
        now = self._clock()
        idle = self._ttl if ttl is None else ttl
        absolute = self._absolute_ttl if ttl is None else ttl
        self._sessions[session_id] = {
            "data": self._encrypt(data),
            "csrf": secrets.token_urlsafe(32),
            "expires_at": now + idle,
            "absolute_expires_at": now + absolute,
            "idle_ttl": idle,
        }
        return session_id

    def deadlines(self, session_id: str) -> tuple[float, float] | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        return session["expires_at"], session["absolute_expires_at"]

    def peek_csrf(self, session_id: str) -> str | None:
        session = self._live(session_id)
        if session is None:
            return None
        return session["csrf"]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self._live(session_id)
        if session is None:
            return None

        now = self._clock()
        session["expires_at"] = min(now + session["idle_ttl"], session["absolute_expires_at"])
        try:
            decrypted = self._decrypt(session["data"])
        except InvalidToken:
            logger.warning("Dropping session because its secret could not be decrypted")
            self._sessions.pop(session_id, None)
            return None
        decrypted["csrf_token"] = session["csrf"]
        return decrypted

    def delete_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    def update_session(self, session_id: str, updates: dict[str, Any]):
        session = self._live(session_id)
        if session is None:
            return
        current = self.get_session(session_id)
        if current is None:
            return
        current.pop("csrf_token", None)
        current.update(updates)
        session["data"] = self._encrypt(current)
        now = self._clock()
        session["expires_at"] = min(now + session["idle_ttl"], session["absolute_expires_at"])

    def _live(self, session_id: str) -> dict[str, Any] | None:
        self._cleanup()
        session = self._sessions.get(session_id)
        if session is None:
            return None
        now = self._clock()
        if now > session["expires_at"] or now > session["absolute_expires_at"]:
            self._sessions.pop(session_id, None)
            return None
        return session

    def _encrypt(self, data: dict[str, Any]) -> dict[str, Any]:
        encrypted: dict[str, Any] = {}
        for key, value in data.items():
            if "key" in key.lower() and isinstance(value, str):
                encrypted[key] = self._cipher.encrypt(value.encode()).decode()
            else:
                encrypted[key] = value
        return encrypted

    def _decrypt(self, data: dict[str, Any]) -> dict[str, Any]:
        decrypted: dict[str, Any] = {}
        for key, value in data.items():
            if "key" in key.lower() and isinstance(value, str):
                decrypted[key] = self._cipher.decrypt(value.encode()).decode()
            else:
                decrypted[key] = value
        return decrypted

    def _cleanup(self):
        now = self._clock()
        expired = [
            sid
            for sid, session in self._sessions.items()
            if now > session["expires_at"] or now > session["absolute_expires_at"]
        ]
        for sid in expired:
            del self._sessions[sid]


session_store = SessionStore()
