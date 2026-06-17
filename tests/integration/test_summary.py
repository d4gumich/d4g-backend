from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock spacy.load before importing app
with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_summary_deps():
    # Patch the class directly since it's now imported inline
    with (
        patch("google.genai.Client") as mock_genai_client_class,
        patch("src.shared.summary_generation.settings") as mock_settings,
    ):
        mock_settings.GOOGLE_API_KEY = "mock_key"
        mock_settings.SOCRATES_STANDARD_MODEL = "gemini-1.5-flash"
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        yield {"client": mock_client, "settings": mock_settings}


def test_generate_summary_success(mock_summary_deps):
    """Happy path: Gemini summarizes provided metadata and sentences."""
    mock_res = MagicMock()
    mock_res.text = "Success summary"
    mock_summary_deps["client"].models.generate_content.return_value = mock_res

    response = client.post(
        "/api/v2/products/summary",
        json={
            "ranked_sentences": ["S1", "S2"],
            "themes_detected": ["Health"],
            "top_locations": [{"country": "Sudan"}],
            "_detected_disasters": ["Flood"],
        },
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "Success summary"


def test_generate_summary_empty_input(mock_summary_deps):
    """Edge case: Input contains no sentences or metadata."""
    mock_res = MagicMock()
    mock_res.text = "Empty summary"
    mock_summary_deps["client"].models.generate_content.return_value = mock_res

    response = client.post(
        "/api/v2/products/summary",
        json={
            "ranked_sentences": [],
            "themes_detected": [],
            "top_locations": [],
            "_detected_disasters": [],
        },
    )
    # The service still calls Gemini but with an empty prompt frame.
    # It should return 200 and whatever Gemini or the fallback logic produces.
    assert response.status_code == 200


def test_generate_summary_extreme_length(mock_summary_deps):
    """Stress test: Extremely long list of sentences."""
    mock_res = MagicMock()
    mock_res.text = "Summary of long text"
    mock_summary_deps["client"].models.generate_content.return_value = mock_res

    response = client.post(
        "/api/v2/products/summary",
        json={
            "ranked_sentences": ["Word " * 100] * 50,  # 5000 words
            "themes_detected": ["None"],
            "top_locations": [],
            "_detected_disasters": [],
        },
    )
    assert response.status_code == 200


def test_generate_summary_partial_missing_fields(mock_summary_deps):
    """Edge case: Payload with empty lists for optional metadata fields."""
    mock_res = MagicMock()
    mock_res.text = "Partial summary"
    mock_summary_deps["client"].models.generate_content.return_value = mock_res

    # Send required fields as per schema
    response = client.post(
        "/api/v2/products/summary",
        json={"ranked_sentences": ["Just this"], "themes_detected": [], "top_locations": [], "_detected_disasters": []},
    )
    assert response.status_code == 200
    assert response.json()["summary"] == "Partial summary"
