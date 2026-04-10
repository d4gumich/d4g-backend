from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Mock spacy.load before importing app
with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@patch("src.lighthouse.service.Client")
def test_lighthouse_analyze_text(mock_gradio_client):
    # Setup mock gradio client
    mock_instance = MagicMock()
    mock_instance.predict.return_value = (
        ["Python", "FastAPI"],
        ["Software Engineer"],
        ["Keep up the good work"],
    )
    mock_gradio_client.return_value = mock_instance

    response = client.post(
        "/api/v1/products/lighthouse/analyze-text",
        json={
            "resume_text": "I am a developer with experience in Python.",
            "sanitize": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Python" in data["extracted_skills"]
    assert data["top_jobs"] == ["Software Engineer"]


def test_lighthouse_status():
    # Mock the api on the existing lighthouse_service instance
    from src.lighthouse.service import lighthouse_service

    mock_api_instance = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.stage = "RUNNING"
    mock_runtime.hardware = "cpu-basic"
    mock_api_instance.get_space_runtime.return_value = mock_runtime

    with patch.object(lighthouse_service, "api", mock_api_instance):
        response = client.get("/api/v1/products/lighthouse/status")

        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == "RUNNING"
        assert "Successfully fetched status" in data["message"]


def test_lighthouse_pause():
    # Mock the api on the existing lighthouse_service instance
    from src.lighthouse.service import lighthouse_service

    mock_api_instance = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.stage = "PAUSED"
    mock_runtime.hardware = "cpu-basic"
    mock_api_instance.get_space_runtime.return_value = mock_runtime

    with patch.object(lighthouse_service, "api", mock_api_instance):
        response = client.post("/api/v1/products/lighthouse/pause")

        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == "PAUSED"
        mock_api_instance.pause_space.assert_called_once()


@patch("src.lighthouse.service.pdfplumber.open")
def test_lighthouse_parse_pdf(mock_pdfplumber):
    # Setup mock pdfplumber
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Extracted resume text"
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__.return_value = mock_pdf
    mock_pdfplumber.return_value = mock_pdf

    response = client.post(
        "/api/v1/products/lighthouse/parse-pdf",
        data={"sanitize": "false"},
        files={"file": ("resume.pdf", b"pdf content", "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["extracted_text"] == "Extracted resume text"
