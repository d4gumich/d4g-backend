from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app, base_url="https://testserver")


@pytest.fixture
def valid_key():
    async def _validate(provider, model, api_key):
        return True, ""

    with patch("src.auth.router.validate_key", _validate):
        yield


def _open_session(api_key="super-secret-value", provider="google"):
    response = client.post(
        "/api/v1/auth/session",
        json={"provider": provider, "model": "gemini-2.5-flash-lite", "api_key": api_key},
    )
    assert response.status_code == 200, response.text
    return response


def test_personal_session_hides_the_key_and_requires_csrf(valid_key):
    opened = _open_session()
    body = opened.json()
    assert body["status"] == "success"
    assert body["csrf_token"]
    assert "session_id" not in body
    assert "super-secret-value" not in opened.text
    cookie = opened.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=none" in cookie
    assert "path=/" in cookie

    status = client.get("/api/v1/auth/status")
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["key_source"] == "personal"
    assert status_body["csrf_token"] == body["csrf_token"]
    assert "super-secret-value" not in status.text
    idle_at = datetime.fromisoformat(status_body["expires_at"])
    absolute_at = datetime.fromisoformat(status_body["absolute_expires_at"])
    assert absolute_at > idle_at

    blocked = client.post("/api/v1/products/owl", json={"text": "flood reports"})
    assert blocked.status_code == 403

    captured = {}

    async def fake_ask(**kwargs):
        captured["api_key"] = kwargs.get("api_key")
        return {
            "data": [],
            "query": {},
            "gemini": {"answer": "ok", "model": "gemini-2.5-flash-lite", "temperature": 0.5},
        }

    with patch("src.owl.router.owl_service.ask_owl", fake_ask):
        allowed = client.post(
            "/api/v1/products/owl",
            json={"text": "flood reports"},
            headers={"X-CSRF-Token": body["csrf_token"]},
        )
    assert allowed.status_code == 200
    assert captured["api_key"] == "super-secret-value"

    logged_out = client.post("/api/v1/auth/logout")
    assert logged_out.status_code == 200
    with patch("src.owl.router.owl_service.ask_owl", fake_ask):
        after = client.post(
            "/api/v1/products/owl",
            json={"text": "flood reports"},
            headers={"X-CSRF-Token": body["csrf_token"]},
        )
    assert after.status_code == 200
    assert captured["api_key"] is None


def test_hangul_ignores_a_key_sent_in_the_form(valid_key):
    opened = _open_session()
    token = opened.json()["csrf_token"]
    seen = {}

    def fake_detect(file_content, kw_num, api_key, instruct_dict, model_name=None):
        seen["api_key"] = api_key
        seen["instruct"] = instruct_dict
        return {"metadata": {}}

    with patch("src.hangul.router.service.detect_v2", fake_detect):
        response = client.post(
            "/api/v2/products/hangul",
            files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
            data={"kw_num": "5", "my_API_key": "form-key-should-not-be-used"},
            headers={"X-CSRF-Token": token},
        )
    assert response.status_code == 200, response.text
    assert seen["api_key"] == "super-secret-value"
    assert "my_api_key" not in seen["instruct"]
    assert "form-key-should-not-be-used" not in response.text
    client.post("/api/v1/auth/logout")


def test_chetah_rejects_an_api_key_field():
    response = client.post("/api/v1/products/chetah", json={"query": "shelter", "api_key": "nope"})
    assert response.status_code == 422


def test_model_errors_do_not_echo_the_key():
    async def explode(provider, api_key=None):
        raise RuntimeError(f"401 rejected {api_key}")

    with patch("src.auth.router.fetch_available_models", explode):
        response = client.post(
            "/api/v1/auth/models",
            json={"provider": "google", "api_key": "super-secret-value"},
        )
    assert response.status_code == 401
    assert "super-secret-value" not in response.text


def test_standard_lighthouse_requires_a_personal_gemini_session(valid_key):
    missing = client.post("/api/v1/products/lighthouse/standard/analyze", json={"resume_text": "Python"})
    assert missing.status_code == 401

    opened = _open_session(provider="openai")
    token = opened.json()["csrf_token"]
    wrong = client.post(
        "/api/v1/products/lighthouse/standard/analyze",
        json={"resume_text": "Python"},
        headers={"X-CSRF-Token": token},
    )
    assert wrong.status_code == 400
    client.post("/api/v1/auth/logout")

    opened = _open_session()
    token = opened.json()["csrf_token"]
    too_long = client.post(
        "/api/v1/products/lighthouse/standard/analyze",
        json={"resume_text": "a" * 50001},
        headers={"X-CSRF-Token": token},
    )
    assert too_long.status_code == 413

    pipeline = AsyncMock(
        return_value={
            "extracted_skills": ["Python"],
            "top_jobs": [],
            "recommendations": ["1. Analyst"],
            "status": "success",
            "engine": "standard",
        }
    )
    with patch("src.lighthouse.standard_router.run_standard_pipeline", pipeline):
        analyzed = client.post(
            "/api/v1/products/lighthouse/standard/analyze",
            json={"resume_text": "Python"},
            headers={"X-CSRF-Token": token},
        )
    assert analyzed.status_code == 200, analyzed.text
    assert analyzed.json()["engine"] == "standard"
    pipeline.assert_awaited()
    client.post("/api/v1/auth/logout")


def test_standard_analysis_is_limited_per_session(valid_key):
    from src.lighthouse.standard_router import standard_analysis_attempts

    opened = _open_session()
    token = opened.json()["csrf_token"]
    standard_analysis_attempts.hits.clear()
    standard_analysis_attempts.limit = 1
    pipeline = AsyncMock(
        return_value={
            "extracted_skills": ["Python"],
            "top_jobs": [],
            "recommendations": ["1. Analyst"],
            "status": "success",
            "engine": "standard",
        }
    )
    try:
        with patch("src.lighthouse.standard_router.run_standard_pipeline", pipeline):
            first = client.post(
                "/api/v1/products/lighthouse/standard/analyze",
                json={"resume_text": "Python"},
                headers={"X-CSRF-Token": token},
            )
            second = client.post(
                "/api/v1/products/lighthouse/standard/analyze",
                json={"resume_text": "Python"},
                headers={"X-CSRF-Token": token},
            )
        assert first.status_code == 200, first.text
        assert second.status_code == 429
        assert "super-secret-value" not in second.text
    finally:
        standard_analysis_attempts.limit = 12
        standard_analysis_attempts.hits.clear()
        client.post("/api/v1/auth/logout")


def test_experimental_key_comparison_rejects_a_mismatch(monkeypatch):
    from src.core.settings import settings

    monkeypatch.setattr(settings, "EXPERIMENTAL_ACCESS_KEY", "correct-experimental-key")
    rejected = client.post(
        "/api/v1/auth/lighthouse-session",
        json={"provider": "hf", "model": "lighthouse", "api_key": "wrong-key"},
    )
    assert rejected.status_code == 401
    assert "correct-experimental-key" not in rejected.text
    accepted = client.post(
        "/api/v1/auth/lighthouse-session",
        json={"provider": "hf", "model": "lighthouse", "api_key": "correct-experimental-key"},
    )
    assert accepted.status_code == 200
    assert "correct-experimental-key" not in accepted.text
    status = client.get("/api/v1/auth/lighthouse-status")
    assert status.json()["status"] == "active"
    assert "correct-experimental-key" not in status.text
    client.post("/api/v1/auth/logout", headers={"X-Lighthouse-CSRF-Token": accepted.json()["csrf_token"]})
