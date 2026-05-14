from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock spacy.load before importing app
with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_pdf_bytes():
    return b"%PDF-1.4 test pdf content"


@patch("src.hangul.service.fitz.open")
@patch("src.hangul.service.title_detection.print_titles")
@patch("src.hangul.service.summary_generation.make_summary_with_API")
def test_hangul_v2_success(mock_summary, mock_titles, mock_fitz, mock_pdf_bytes):
    """Happy path for Hangul v2: Extract metadata, title, and summary."""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "This is a test page content about a disaster in Geneva."
    mock_doc.__iter__.return_value = [mock_page]
    mock_doc.page_count = 1
    mock_doc.metadata = {"author": "Test Author", "creationDate": "D:20230101120000Z"}
    mock_fitz.return_value = mock_doc

    mock_titles.return_value = (["Test Title"], "Page 1 Text")
    mock_summary.return_value = "This is a mocked summary."

    with patch("src.hangul.service.settings") as mock_settings, patch(
        "src.hangul.service.theme_detection.detect_theme"
    ) as mock_themes, patch("src.hangul.service.new_disaster_detection.disaster_prediction") as mock_disasters:
        mock_settings.THEME_MODEL_PATH = "mock_path"
        mock_themes.return_value = ["Health"]
        mock_disasters.return_value = ["Flood"]

        response = client.post(
            "/api/v2/products/hangul",
            data={"kw_num": 5, "document_title": "true", "document_summary": "true"},
            files={"file": ("test.pdf", mock_pdf_bytes, "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_title"] == ["Test Title"]
        assert data["metadata"]["Author"] == "Test Author"


def test_hangul_corrupted_pdf():
    """Edge case: File is not a valid PDF (corrupted)."""
    with patch("src.hangul.service.fitz.open", side_effect=RuntimeError("Cannot open PDF")):
        response = client.post(
            "/api/v2/products/hangul",
            data={"kw_num": 5},
            files={"file": ("bad.pdf", b"not a pdf", "application/pdf")},
        )
        assert response.status_code == 500
        # Check that the global exception handler caught it
        assert "Cannot open PDF" in response.json()["detail"]


def test_hangul_missing_metadata(mock_pdf_bytes):
    """Edge case: PDF opens but has zero metadata fields or pages."""
    mock_doc = MagicMock()
    mock_doc.metadata = {}  # Empty metadata
    mock_doc.page_count = 0
    mock_doc.__iter__.return_value = []

    with patch("src.hangul.service.fitz.open", return_value=mock_doc):
        response = client.post(
            "/api/v2/products/hangul",
            data={"kw_num": 5, "document_title": "true", "document_summary": "true"},
            files={"file": ("empty.pdf", mock_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["Author"] == "Item could not be extracted. Please submit a bug report if concerned."
        assert data["document_title"] == []


@patch("tika.parser.from_buffer")
def test_hangul_v1_tika_failure(mock_tika, mock_pdf_bytes):
    """Edge case: Tika server returns None or fails."""
    mock_tika.return_value = None
    response = client.post(
        "/api/v1/products/hangul",
        data={"kw_num": 3},
        files={"file": ("test.pdf", mock_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 500
