import base64
import hashlib
import logging
import time
from typing import Any
from uuid import uuid4

from cryptography.fernet import Fernet

from src.core.settings import settings

logger = logging.getLogger(__name__)

# Use a stable key if provided in settings, otherwise generate one
# We derive a 32-byte base64 key from the stable secret to satisfy Fernet's requirements
if settings.OWL_GOOGLE_API_KEY:
    key_hash = hashlib.sha256(settings.OWL_GOOGLE_API_KEY.encode()).digest()
    _MASTER_KEY = base64.urlsafe_b64encode(key_hash)
else:
    _MASTER_KEY = Fernet.generate_key()

_cipher = Fernet(_MASTER_KEY)


class SessionStore:
    def __init__(self, ttl: int = 1800):  # Default 30 minutes
        self._sessions: dict[str, dict[str, Any]] = {}
        self._ttl = ttl

    def create_session(self, data: dict[str, Any], ttl: int | None = None) -> str:
        session_id = str(uuid4())

        # Encrypt any potential sensitive data (keys)
        encrypted_data = {}
        for k, v in data.items():
            if "key" in k.lower() and isinstance(v, str):
                encrypted_data[k] = _cipher.encrypt(v.encode()).decode()
            else:
                encrypted_data[k] = v

        actual_ttl = ttl if ttl is not None else self._ttl
        self._sessions[session_id] = {"data": encrypted_data, "expires_at": time.time() + actual_ttl}
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        self._cleanup()
        session = self._sessions.get(session_id)
        if not session:
            return None

        if time.time() > session["expires_at"]:
            del self._sessions[session_id]
            return None

        # Refresh TTL on access
        session["expires_at"] = time.time() + self._ttl

        # Decrypt sensitive data
        decrypted_data = {}
        for k, v in session["data"].items():
            if "key" in k.lower() and isinstance(v, str):
                try:
                    decrypted_data[k] = _cipher.decrypt(v.encode()).decode()
                except Exception:
                    decrypted_data[k] = v
            else:
                decrypted_data[k] = v

        return decrypted_data

    def delete_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]

    def update_session(self, session_id: str, updates: dict[str, Any]):
        session = self._sessions.get(session_id)
        if not session:
            return

        for k, v in updates.items():
            if "key" in k.lower() and isinstance(v, str):
                session["data"][k] = _cipher.encrypt(v.encode()).decode()
            else:
                session["data"][k] = v

        # Refresh TTL on update
        session["expires_at"] = time.time() + self._ttl

    def _cleanup(self):
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if now > s["expires_at"]]
        for sid in expired:
            del self._sessions[sid]


# Global session store instance
session_store = SessionStore()
