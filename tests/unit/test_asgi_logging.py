import logging
import re
from datetime import datetime, timezone
from io import StringIO

from src.shared.asgi_logging import UtcFormatter, build_stream_handlers, install_asgi_logging

_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}Z ", re.MULTILINE)


def _record(level: int, message: str) -> logging.LogRecord:
    record = logging.LogRecord(
        name="d4g.access",
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    record.created = datetime(2026, 11, 5, 17, 22, 41, tzinfo=timezone.utc).timestamp()
    record.msecs = 0
    return record


def test_lines_start_with_a_utc_timestamp_and_the_level():
    formatter = UtcFormatter("%(asctime)s %(levelname)-8s %(name)s %(message)s")
    text = formatter.format(_record(logging.INFO, "GET /health 200 0.42ms ref=abc"))
    assert text == "2026-11-05 17:22:41Z INFO     d4g.access GET /health 200 0.42ms ref=abc"
    error = formatter.format(_record(logging.ERROR, "Qdrant is not configured."))
    assert error.startswith("2026-11-05 17:22:41Z ERROR    d4g.access ")


def test_info_stays_on_stdout_and_errors_go_to_stderr():
    stdout, stderr = StringIO(), StringIO()
    info_handler, problem_handler = build_stream_handlers(stdout, stderr)
    log = logging.getLogger("d4g.test.asgi")
    previous_handlers = list(log.handlers)
    previous_level = log.level
    previous_propagate = log.propagate
    log.handlers = [info_handler, problem_handler]
    log.propagate = False
    log.setLevel(logging.INFO)
    try:
        log.info("GET /health 200 0.42ms ref=abc")
        log.warning("SOCRATES_DB_URL not set")
        log.error("Qdrant is not configured.")
    finally:
        log.handlers = previous_handlers
        log.setLevel(previous_level)
        log.propagate = previous_propagate

    info = stdout.getvalue()
    problems = stderr.getvalue()
    assert _STAMP.search(info)
    assert "GET /health 200" in info
    assert " INFO " in info
    assert "Qdrant is not configured." not in info
    assert "SOCRATES_DB_URL" not in info
    assert _STAMP.search(problems)
    assert " WARNING " in problems
    assert "SOCRATES_DB_URL not set" in problems
    assert " ERROR " in problems
    assert "Qdrant is not configured." in problems
    assert "GET /health" not in problems


def test_a_request_line_names_the_method_path_status_and_reference(caplog):
    from fastapi.testclient import TestClient

    from src.main import app

    with caplog.at_level(logging.INFO, logger="d4g.access"):
        response = TestClient(app).get("/health")
    request_id = response.headers["x-request-id"]
    assert response.status_code == 200
    assert "GET /health 200 " in caplog.text
    assert f"ref={request_id}" in caplog.text


def test_install_is_idempotent_and_drops_the_uvicorn_access_copy():
    root = logging.getLogger()
    names = ("uvicorn", "uvicorn.error", "uvicorn.asgi", "uvicorn.access")
    saved = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).level,
            logging.getLogger(name).propagate,
        )
        for name in names
    }
    previous_handlers = list(root.handlers)
    previous_level = root.level
    try:
        install_asgi_logging()
        install_asgi_logging()
        marked = [handler for handler in root.handlers if getattr(handler, "_d4g_asgi_log", False)]
        assert len(marked) == 2
        access = logging.getLogger("uvicorn.access")
        assert access.propagate is False
        assert access.level == logging.WARNING
        assert logging.getLogger("uvicorn.error").propagate is True
    finally:
        root.handlers = previous_handlers
        root.setLevel(previous_level)
        for name, (handlers, level, propagate) in saved.items():
            log = logging.getLogger(name)
            log.handlers = handlers
            log.setLevel(level)
            log.propagate = propagate
