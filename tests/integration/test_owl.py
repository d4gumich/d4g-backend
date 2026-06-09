from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock spacy.load before importing app to avoid heavy model loading in CI
with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_owl_deps():
    with (
        patch("src.owl.service.psycopg2.connect") as mock_connect,
        patch("src.owl.service.genai.GenerativeModel") as mock_genai,
        patch("src.owl.service.get_embed_model") as mock_get_model,
        patch("src.owl.service.settings") as mock_settings,
    ):
        # Setup settings
        mock_settings.OWL_GOOGLE_API_KEY = "mock_key"
        mock_settings.OWL_DB_HOST = "localhost"
        mock_settings.OWL_DB_PORT = 5432
        mock_settings.OWL_DB_USER = "user"
        mock_settings.OWL_DB_NAME = "db"
        mock_settings.OWL_DB_PASSWORD = "pass"
        mock_settings.POSTGRESQL_PASS = "pass"

        # Setup default mocks
        mock_embed_instance = MagicMock()
        mock_get_model.return_value = mock_embed_instance
        mock_encode = mock_embed_instance.encode
        mock_encode.return_value = [0.1] * 384
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_connect.return_value = mock_conn

        mock_model = MagicMock()
        mock_genai.return_value = mock_model

        yield {
            "connect": mock_connect,
            "genai": mock_genai,
            "model": mock_model,
            "encode": mock_encode,
            "cursor": mock_cur,
        }


def test_owl_ask_success(mock_owl_deps):
    """Happy path: DB finds records, Gemini answers."""
    mock_owl_deps["cursor"].fetchall.side_effect = [
        [{"uuid": "1", "cosine_similarity": 0.9}],  # Top matches
        [{"uuid": "1", "title": "Crisis in Sudan", "combined_details": "Flash floods reported in Khartoum."}],
    ]

    mock_res = MagicMock()
    mock_res.text = "There are floods in Khartoum."
    mock_owl_deps["model"].generate_content.return_value = mock_res

    response = client.post("/api/v1/products/owl", json={"text": "Sudan floods", "k": 5})

    assert response.status_code == 200
    data = response.json()
    assert "Khartoum" in data["gemini"]["answer"]
    assert len(data["data"]) == 1


def test_owl_no_results_found(mock_owl_deps):
    """Edge case: Database returns zero matches for the vector search."""
    mock_owl_deps["cursor"].fetchall.return_value = []  # No matches

    response = client.post("/api/v1/products/owl", json={"text": "Alien invasion on Mars"})

    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    # If no results found, rows is empty, it returns the custom message
    assert "No results found" in data["gemini"]["answer"]


def test_owl_gemini_api_failure(mock_owl_deps):
    """Edge case: DB works but Gemini API is down/quota exceeded."""
    # Mock some DB rows first
    mock_owl_deps["cursor"].fetchall.side_effect = [
        [{"uuid": "1", "cosine_similarity": 0.9}],
        [{"uuid": "1", "title": "T1", "combined_details": "C1"}],
    ]
    # Simulate API failure
    mock_owl_deps["model"].generate_content.side_effect = Exception("Gemini Quota Exceeded")

    response = client.post("/api/v1/products/owl", json={"text": "Tell me about T1"})

    assert response.status_code == 200  # Error handled gracefully by _call_gemini_safe returning a string
    data = response.json()
    assert "Gemini call failed" in data["gemini"]["answer"]


def test_owl_invalid_request_payload():
    """Edge case: Missing required 'text' field."""
    response = client.post("/api/v1/products/owl", json={"k": 5})
    assert response.status_code == 422  # Pydantic validation error
