from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Mock spacy.load before importing app
with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@patch("src.summary.service.genai.GenerativeModel")
@patch("src.summary.service.settings")
def test_generate_summary_success(mock_settings, mock_genai):
    # Mock settings
    mock_settings.GOOGLE_API_KEY = "mock_key"

    # Setup mock Gemini
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a summarized version of the report."
    mock_model.generate_content.return_value = mock_response
    mock_genai.return_value = mock_model

    response = client.post(
        "/api/v2/products/summary",
        json={
            "ranked_sentences": ["Sentence 1", "Sentence 2"],
            "themes_detected": ["Food and Nutrition"],
            "top_locations": [{"country": "Ethiopia"}],
            "_detected_disasters": ["Drought"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "This is a summarized version of the report."
    assert data["status"] == "success"


@patch("src.summary.service.genai.GenerativeModel")
@patch("src.summary.service.settings")
def test_generate_summary_api_error(mock_settings, mock_genai):
    # Mock settings
    mock_settings.GOOGLE_API_KEY = "mock_key"

    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("API Key Invalid")
    mock_genai.return_value = mock_model

    response = client.post(
        "/api/v2/products/summary",
        json={
            "ranked_sentences": ["Test content"],
            "themes_detected": [],
            "top_locations": [],
            "_detected_disasters": [],
        },
    )

    assert response.status_code == 200  # App returns error message in JSON
    data = response.json()
    assert "Summarization failed" in data["summary"]
