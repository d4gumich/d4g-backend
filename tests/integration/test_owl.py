from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock spacy.load before importing app to avoid heavy model loading in CI
with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_owl_deps():
    # Patch the classes and functions directly since they are now imported inline
    with (
        patch("src.owl.service.psycopg2.connect") as mock_connect,
        patch("google.genai.Client") as mock_genai_client_class,
        patch("src.owl.service.settings") as mock_settings,
    ):
        # Setup settings
        mock_settings.GOOGLE_API_KEY = "mock_key"
        mock_settings.OWL_GOOGLE_API_KEY = "mock_key"
        mock_settings.OWL_DB_HOST = "localhost"
        mock_settings.OWL_DB_PORT = 5432
        mock_settings.OWL_DB_USER = "user"
        mock_settings.OWL_DB_NAME = "db"
        mock_settings.OWL_DB_PASSWORD = "pass"
        mock_settings.POSTGRESQL_PASS = "pass"

        # Setup Client Mock
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client

        # Setup Embedding Mock
        mock_embed_result = MagicMock()
        mock_embed_result.embeddings = [MagicMock(values=[0.1] * 768)]
        mock_client.models.embed_content.return_value = mock_embed_result

        # Setup Database Mock
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_connect.return_value = mock_conn

        yield {
            "connect": mock_connect,
            "client": mock_client,
            "cursor": mock_cur,
            "settings": mock_settings,
        }


def test_owl_ask_success(mock_owl_deps):
    """Happy path: Ask Owl a question and get results."""
    # Mock database results
    mock_owl_deps["cursor"].fetchall.side_effect = [
        [{"uuid": "1", "cosine_similarity": 0.9}],  # Top matches
        [{"uuid": "1", "title": "Test Doc", "combined_details": "Context content"}],  # Full docs
    ]

    # Mock Gemini response
    mock_owl_deps["client"].models.generate_content.return_value.text = "Mocked answer from Owl."

    response = client.post("/api/v1/products/owl", json={"text": "How to help?", "k": 1})

    assert response.status_code == 200
    data = response.json()
    assert data["gemini"]["answer"] == "Mocked answer from Owl."
    assert len(data["data"]) == 1


def test_owl_no_results_found(mock_owl_deps):
    """Edge case: Database returns no matching documents."""
    mock_owl_deps["cursor"].fetchall.return_value = []

    response = client.post("/api/v1/products/owl", json={"text": "nonexistent", "k": 5})

    assert response.status_code == 200
    data = response.json()
    assert "No results found" in data["gemini"]["answer"]
    assert data["data"] == []


def test_owl_gemini_api_failure(mock_owl_deps):
    """Edge case: Gemini API fails during processing."""
    # Mock DB success
    mock_owl_deps["cursor"].fetchall.side_effect = [
        [{"uuid": "1", "cosine_similarity": 0.8}],
        [{"uuid": "1", "title": "Test", "combined_details": "..."}],
    ]

    # Mock Gemini failure
    mock_owl_deps["client"].models.generate_content.side_effect = Exception("Gemini Down")

    response = client.post("/api/v1/products/owl", json={"text": "Help", "k": 1})

    assert response.status_code == 200
    assert "Gemini call failed" in response.json()["gemini"]["answer"]


def test_owl_invalid_request_payload():
    """Edge case: Missing required 'text' field."""
    response = client.post("/api/v1/products/owl", json={"k": 5})
    assert response.status_code == 422  # Pydantic validation error
