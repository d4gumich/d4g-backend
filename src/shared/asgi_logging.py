"""Format ASGI logs for PythonAnywhere's three log files.

The front proxy already writes access.log with a timestamp. stderr is copied to
error.log and stdout is copied to server.log. Uvicorn's own lines have no time,
and its stderr logger is named uvicorn.error even for INFO.

INFO stays on stdout. WARNING and above stay on stderr. Each line starts with
a UTC timestamp and the level, so the two files can be read on their own.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import TextIO

_HANDLER_MARK = "_d4g_asgi_log"
_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"


class UtcFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        del datefmt
        moment = datetime.fromtimestamp(record.created, timezone.utc)
        return moment.strftime("%Y-%m-%d %H:%M:%S") + "Z"


class AtMostInfo(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= logging.INFO


def build_stream_handlers(stdout: TextIO, stderr: TextIO) -> tuple[logging.Handler, logging.Handler]:
    formatter = UtcFormatter(_FORMAT)
    info_handler = logging.StreamHandler(stdout)
    info_handler.setLevel(logging.INFO)
    info_handler.addFilter(AtMostInfo())
    problem_handler = logging.StreamHandler(stderr)
    problem_handler.setLevel(logging.WARNING)
    for handler in (info_handler, problem_handler):
        handler.setFormatter(formatter)
        setattr(handler, _HANDLER_MARK, True)
    return info_handler, problem_handler


def install_asgi_logging() -> None:
    root = logging.getLogger()
    if any(getattr(handler, _HANDLER_MARK, False) for handler in root.handlers):
        return
    info_handler, problem_handler = build_stream_handlers(sys.stdout, sys.stderr)
    root.setLevel(logging.INFO)
    root.addHandler(info_handler)
    root.addHandler(problem_handler)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.asgi"):
        log = logging.getLogger(name)
        log.handlers.clear()
        log.propagate = True
        log.setLevel(logging.INFO)
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False
    access.setLevel(logging.WARNING)
