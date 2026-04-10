from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Mock spacy.load before importing app
with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@patch("src.owl.service.psycopg2.connect")
@patch("src.owl.service.genai.GenerativeModel")
@patch("src.owl.service._embed_model.encode")
@patch("src.owl.service.settings")
def test_owl_ask_success(mock_settings, mock_encode, mock_genai, mock_connect):
    # Mock settings
    mock_settings.OWL_GOOGLE_API_KEY = "mock_key"
    mock_settings.OWL_DB_HOST = "localhost"
    mock_settings.OWL_DB_PORT = 5432
    mock_settings.OWL_DB_USER = "user"
    mock_settings.OWL_DB_NAME = "db"
    mock_settings.OWL_DB_PASSWORD = "pass"
    mock_settings.POSTGRESQL_PASS = "pass"

    # Mock embedding
    mock_encode.return_value = [0.1] * 384

    # Mock DB
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.fetchall.side_effect = [
        [{"uuid": "1", "cosine_similarity": 0.9}],  # Top matches
        [{"uuid": "1", "title": "Test Report", "combined_details": "Context content"}],  # Full rows
    ]
    mock_conn.cursor.return_value = mock_cur
    mock_connect.return_value = mock_conn

    # Mock Gemini
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is the AI answer from context."
    mock_model.generate_content.return_value = mock_response
    mock_genai.return_value = mock_model

    response = client.post("/api/v1/products/owl", json={"text": "What is the situation in Sudan?", "k": 5})

    assert response.status_code == 200
    data = response.json()
    assert data["gemini"]["answer"] == "This is the AI answer from context."
    assert len(data["data"]) == 1
    assert data["data"][0]["title"] == "Test Report"


@patch("src.owl.service.psycopg2.connect")
def test_owl_db_error(mock_connect):
    mock_connect.side_effect = Exception("DB Connection Failed")

    response = client.post("/api/v1/products/owl", json={"text": "Hello"})

    assert response.status_code == 200  # App handles error gracefully
    data = response.json()
    assert "error" in data
    assert "DB Connection Failed" in data["error"]
