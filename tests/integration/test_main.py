import logging
import re

from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

from src.main import app

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from d4g-backend (FastAPI)"}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert re.fullmatch(r"[A-Za-z0-9_-]{8,64}", response.headers["x-request-id"])


def test_a_safe_request_id_is_kept_and_exposed():
    response = client.get("/health", headers={"X-Request-ID": "abc_DEF-1234"})
    assert response.headers["x-request-id"] == "abc_DEF-1234"
    cors = next(layer for layer in app.user_middleware if layer.cls is CORSMiddleware)
    assert "X-Request-ID" in cors.kwargs["allow_headers"]
    assert "X-Request-ID" in cors.kwargs["expose_headers"]


def test_an_unsafe_request_id_is_replaced():
    response = client.get("/health", headers={"X-Request-ID": "bad id"})
    assert re.fullmatch(r"[a-f0-9]{12}", response.headers["x-request-id"])


def test_unhandled_exception_returns_a_reference_and_redacts_the_log(caplog):
    @app.get("/__log_safety_boom")
    def _boom():
        raise RuntimeError("provider said AIzaSyA1234567890123456789012")

    quiet = TestClient(app, raise_server_exceptions=False)
    try:
        with caplog.at_level(logging.ERROR):
            response = quiet.get("/__log_safety_boom")
    finally:
        app.router.routes = [
            route for route in app.router.routes if getattr(route, "path", None) != "/__log_safety_boom"
        ]

    assert response.status_code == 500
    body = response.json()
    assert body["message"] == "Something went wrong. Try again in a moment."
    assert body["request_id"] == response.headers["x-request-id"]
    assert "AIzaSyA" not in response.text
    assert "AIzaSyA" not in caplog.text
    assert body["request_id"] in caplog.text
