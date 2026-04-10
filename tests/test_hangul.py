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
    # Setup mock PDF
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "This is a test page content about a disaster in Geneva."
    mock_doc.__iter__.return_value = [mock_page]
    mock_doc.page_count = 1
    mock_doc.metadata = {"author": "Test Author", "creationDate": "D:20230101120000Z"}
    mock_fitz.return_value = mock_doc

    mock_titles.return_value = (["Test Title"], "Page 1 Text")
    mock_summary.return_value = "This is a mocked summary."

    # Mock settings to ensure they exist
    with (
        patch("src.hangul.service.settings") as mock_settings,
        patch("src.hangul.service.theme_detection.detect_theme") as mock_themes,
        patch("src.hangul.service.new_disaster_detection.disaster_prediction") as mock_disasters,
    ):
        mock_settings.THEME_MODEL_PATH = "mock_path"
        mock_settings.THEME_VECTORIZER_PATH = "mock_path"
        mock_settings.DISASTER_MODEL_PATH = "mock_path"
        mock_settings.DISASTER_VECTORIZER_PATH = "mock_path"

        mock_themes.return_value = ["Health"]
        mock_disasters.return_value = ["Flood"]

        response = client.post(
            "/api/v2/products/hangul",
            data={
                "kw_num": 5,
                "document_title": "true",
                "document_summary": "true",
                "document_theme": "true",
                "new_detected_disasters": "true",
            },
            files={"file": ("test.pdf", mock_pdf_bytes, "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_title"] == ["Test Title"]
        assert data["document_summary"] == "This is a mocked summary."
        assert "Health" in data["document_theme"]
        assert "Flood" in data["new_detected_disasters"]
        assert data["metadata"]["Author"] == "Test Author"


@patch("tika.parser.from_buffer")
@patch("tika.initVM", MagicMock())
def test_hangul_v1_success(mock_tika_parser, mock_pdf_bytes):
    # Setup mock tika response
    mock_tika_parser.return_value = {
        "metadata": {
            "Author": "Tika Author",
            "xmpTPg:NPages": "1",
            "pdf:charsPerPage": ["100"],
            "Content-Type": "application/pdf",
            "Creation-Date": "2023-01-01T12:00:00Z",
        },
        "content": '<div class="page"><p>Tika content</p></div>',
    }

    with (
        patch("src.hangul.service.detected_potential_countries") as mock_loc,
        patch("src.hangul.service.get_disasters") as mock_dis,
    ):
        mock_loc.return_value = {
            "Switzerland": {"no_of_occurences": 1},
            "GLOBAL": False,
            "REGIONAL": False,
        }
        mock_dis.return_value = ["Earthquake"]

        response = client.post(
            "/api/v1/products/hangul",
            data={"kw_num": 3},
            files={"file": ("test.pdf", mock_pdf_bytes, "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["Author"] == "Tika Author"
        assert data["disasters"] == ["Earthquake"]
