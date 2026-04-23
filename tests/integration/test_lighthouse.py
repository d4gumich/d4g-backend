from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Mock spacy.load before importing app
with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@patch("src.lighthouse.service.Client")
def test_lighthouse_analyze_text_success(mock_gradio_client):
    """Happy path for text analysis via Gradio."""
    mock_instance = MagicMock()
    mock_instance.predict.return_value = (["Python"], ["Engineer"], ["Good"])
    mock_gradio_client.return_value = mock_instance

    response = client.post(
        "/api/v1/products/lighthouse/analyze-text",
        json={"resume_text": "Python developer", "sanitize": False},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@patch("src.lighthouse.service.Client")
def test_lighthouse_gradio_failure(mock_gradio_client):
    """Edge case: Hugging Face / Gradio space is down or times out."""
    mock_instance = MagicMock()
    mock_instance.predict.side_effect = Exception("Hugging Face Space Offline")
    mock_gradio_client.return_value = mock_instance

    response = client.post("/api/v1/products/lighthouse/analyze-text", json={"resume_text": "Any text"})
    assert response.status_code == 502
    assert "Space Offline" in response.json()["detail"]


@patch("src.lighthouse.service.pdfplumber.open")
def test_lighthouse_parse_corrupted_pdf(mock_pdfplumber):
    """Edge case: pdfplumber fails to parse the provided file."""
    mock_pdfplumber.side_effect = Exception("Invalid PDF structure")

    response = client.post(
        "/api/v1/products/lighthouse/parse-pdf",
        data={"sanitize": "false"},
        files={"file": ("bad.pdf", b"corrupt", "application/pdf")},
    )
    assert response.status_code == 500
    assert "Invalid PDF structure" in response.json()["detail"]


def test_lighthouse_status_error_handling():
    """Edge case: Failed to fetch space status from HF API."""
    from src.lighthouse.service import lighthouse_service

    mock_api = MagicMock()
    mock_api.get_space_runtime.side_effect = Exception("HF API Error")

    with patch.object(lighthouse_service, "api", mock_api):
        response = client.get("/api/v1/products/lighthouse/status")
        assert response.status_code == 502
