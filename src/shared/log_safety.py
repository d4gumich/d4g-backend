"""Redact secrets from log records and attach a request reference.

The filter runs for every logger. It removes configured server secrets, secrets
remembered for the current request, and common provider-key shapes. Tracebacks
are redacted too, because the exception text is appended after the message.
"""

import logging
import re
import uuid
from collections.abc import Callable
from contextvars import ContextVar

from src.core.settings import settings

_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_log_secrets: ContextVar[tuple[str, ...]] = ContextVar("log_secrets", default=())

_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_MIN_SECRET_LENGTH = 8

_SECRET_SETTINGS = (
    "EXPERIMENTAL_ACCESS_KEY",
    "HF_TOKEN",
    "QDRANT_API_KEY",
    "GOOGLE_API_KEY",
    "OWL_GOOGLE_API_KEY",
    "SESSION_ENCRYPTION_KEY",
    "LIGHTHOUSE_SCHEDULER_TOKEN",
    "OWL_DB_PASSWORD",
    "POSTGRESQL_PASS",
)

_PATTERNS = (
    (re.compile(r"AIza[0-9A-Za-z\-_]{20,}"), "[redacted]"),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"), "[redacted]"),
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "[redacted]"),
    (re.compile(r"\bhf_[A-Za-z0-9]{20,}"), "[redacted]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-~+/]+=*"), "Bearer [redacted]"),
    (
        re.compile(r"""(?i)((?:["']?(?:api[_-]?key|access[_-]?token|authorization)["']?\s*[:=]\s*)["'])([^"']{6,})"""),
        r"\1[redacted]",
    ),
    (
        re.compile(r"(?i)((?:api[_-]?key|access[_-]?token)\s*[:=]\s*)([^\s&,'\"]{6,})"),
        r"\1[redacted]",
    ),
)

_Handle = Callable[[logging.Logger, logging.LogRecord], None]
_original_handle: _Handle | None = None


def accept_request_id(header: str | None) -> str:
    if isinstance(header, str) and _REQUEST_ID.fullmatch(header.strip()):
        return header.strip()
    return uuid.uuid4().hex[:12]


def current_request_id() -> str:
    return _request_id.get()


def begin_request_log(header: str | None) -> tuple[str, object, object]:
    request_id = accept_request_id(header)
    return request_id, _request_id.set(request_id), _log_secrets.set(())


def finish_request_log(id_token: object, secret_token: object) -> None:
    _request_id.reset(id_token)  # type: ignore[arg-type]
    _log_secrets.reset(secret_token)  # type: ignore[arg-type]


def remember_log_secret(secret: str | None) -> None:
    if not isinstance(secret, str) or len(secret) < _MIN_SECRET_LENGTH:
        return
    current = _log_secrets.get()
    if secret in current:
        return
    _log_secrets.set((*current, secret))


def _configured_secrets() -> list[str]:
    found: list[str] = []
    for name in _SECRET_SETTINGS:
        value = getattr(settings, name, None)
        if isinstance(value, str) and len(value) >= _MIN_SECRET_LENGTH:
            found.append(value)
    database_url = getattr(settings, "SOCRATES_DB_URL", None)
    if (
        isinstance(database_url, str)
        and "://" in database_url
        and "@" in database_url
        and len(database_url) >= _MIN_SECRET_LENGTH
    ):
        found.append(database_url)
    for value in _log_secrets.get():
        if value not in found:
            found.append(value)
    return sorted(set(found), key=len, reverse=True)


def redact_text(text: str) -> str:
    if not text:
        return ""
    redacted = text
    for secret in _configured_secrets():
        if secret and secret in redacted:
            redacted = redacted.replace(secret, "[redacted]")
    for pattern, replacement in _PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_record(record: logging.LogRecord) -> None:
    if getattr(record, "_secrets_redacted", False):
        return
    try:
        message = record.getMessage()
    except Exception:
        message = str(record.msg)
    redacted = redact_text(message)
    record.msg = redacted
    record.args = ()
    record.message = redacted
    if record.exc_info and not record.exc_text:
        record.exc_text = logging.Formatter().formatException(record.exc_info)
    if record.exc_text:
        record.exc_text = redact_text(record.exc_text)
    record.exc_info = None
    if record.stack_info:
        record.stack_info = redact_text(record.stack_info)
    record._secrets_redacted = True  # type: ignore[attr-defined]


def install_log_redaction() -> None:
    global _original_handle
    if _original_handle is not None:
        return
    _original_handle = logging.Logger.handle

    def _redacting_handle(self: logging.Logger, record: logging.LogRecord) -> None:
        redact_record(record)
        _original_handle(self, record)

    logging.Logger.handle = _redacting_handle  # type: ignore[method-assign]
