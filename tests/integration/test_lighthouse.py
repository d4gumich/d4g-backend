from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.settings import settings

# Mock spacy.load before importing app
with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Provides a valid experimental API key for testing, patching settings if needed."""
    test_key = settings.EXPERIMENTAL_ACCESS_KEY or "d4g-test-key"
    with patch.object(settings, "EXPERIMENTAL_ACCESS_KEY", test_key):
        yield {"X-Experimental-API-Key": test_key}


@patch("src.lighthouse.service.Client")
def test_lighthouse_analyze_text_success(mock_gradio_client, auth_headers):
    """Happy path for text analysis via Gradio."""
    mock_instance = MagicMock()
    mock_instance.predict.return_value = (["Python"], ["Engineer"], ["Good"])
    mock_gradio_client.return_value = mock_instance

    response = client.post(
        "/api/v1/products/lighthouse/analyze-text",
        json={"resume_text": "Python developer", "sanitize": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@patch("src.lighthouse.service.Client")
def test_lighthouse_gradio_failure(mock_gradio_client, auth_headers, caplog):
    """Edge case: Hugging Face / Gradio space is down or times out."""
    mock_instance = MagicMock()
    mock_instance.predict.side_effect = Exception("Hugging Face Space Offline")
    mock_gradio_client.return_value = mock_instance

    with caplog.at_level("ERROR"):
        response = client.post(
            "/api/v1/products/lighthouse/analyze-text", json={"resume_text": "Any text"}, headers=auth_headers
        )
    assert response.status_code == 502
    assert response.json()["detail"] == "The analysis service is unavailable. Wait a minute and try again."
    assert "Space Offline" not in response.text
    assert "Space Offline" in caplog.text
    assert response.headers["x-request-id"]


@patch("src.lighthouse.service.pdfplumber.open")
def test_lighthouse_parse_accepts_only_a_pdf_and_hides_parser_errors(mock_pdfplumber, auth_headers, caplog):
    mock_pdfplumber.side_effect = Exception("Invalid PDF structure secret snippet")

    with caplog.at_level("ERROR"):
        broken = client.post(
            "/api/v1/products/lighthouse/parse-pdf",
            data={"sanitize": "false"},
            files={"file": ("bad.pdf", b"%PDF-1.4 not really", "application/pdf")},
            headers=auth_headers,
        )
        rejected = client.post(
            "/api/v1/products/lighthouse/parse-pdf",
            data={"sanitize": "false"},
            files={"file": ("notes.txt", b"hello", "application/pdf")},
            headers=auth_headers,
        )

    assert broken.status_code == 400
    assert broken.json()["detail"] == "The PDF could not be read."
    assert "Invalid PDF structure" not in broken.text
    assert "secret snippet" not in broken.text
    assert "Invalid PDF structure" not in caplog.text
    assert "Exception" in caplog.text
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "The PDF could not be read."
    mock_pdfplumber.assert_called_once()


def test_experimental_resume_and_pdf_keep_the_same_size_cap(auth_headers):
    with (
        patch("src.lighthouse.router.MAX_RESUME_CHARS", 5),
        patch("src.lighthouse.router.MAX_PDF_BYTES", 8),
        patch("src.lighthouse.router.lighthouse_service.analyze") as analyze,
        patch("src.lighthouse.router.lighthouse_service.parse_pdf") as parse_pdf,
    ):
        analyzed = client.post(
            "/api/v1/products/lighthouse/analyze-text",
            json={"resume_text": "too-long"},
            headers=auth_headers,
        )
        uploaded = client.post(
            "/api/v1/products/lighthouse/parse-pdf",
            data={"sanitize": "false"},
            files={"file": ("resume.pdf", b"0123456789", "application/pdf")},
            headers=auth_headers,
        )
    assert analyzed.status_code == 413
    assert analyzed.json()["detail"] == "Resume text is too long."
    assert uploaded.status_code == 413
    assert uploaded.json()["detail"] == "PDF is too large."
    analyze.assert_not_called()
    parse_pdf.assert_not_called()


def test_lighthouse_status_error_handling(auth_headers):
    """Edge case: Failed to fetch space status from HF API."""
    from src.lighthouse.service import lighthouse_service

    mock_api = MagicMock()
    mock_api.get_space_runtime.side_effect = Exception("HF API Error")

    with patch.object(lighthouse_service, "api", mock_api):
        response = client.get("/api/v1/products/lighthouse/status", headers=auth_headers)
        assert response.status_code == 502
        assert response.json()["detail"] == "The engine status could not be read. Try again in a moment."
        assert "HF API Error" not in response.text
