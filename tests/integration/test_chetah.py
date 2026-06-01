from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

# Mock spacy.load before anything else
with patch("spacy.load", MagicMock()):
    from src.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_chetah_data():
    # Mock the loaded data in the service module directly
    mock_df = pd.DataFrame(
        {
            "Title": ["Test Title 1"],
            "Date": ["2023-01-01"],
            "URL": ["http://test.com"],
            "cluster": ["1"],
            "summary": ["This is a test summary about disasters."],
        }
    )

    mock_doc_table = {
        "1": {
            "report_title": ["Test Title V2"],
            "doc_creation_date": "2023-01-01",
            "URL": "http://testv2.com",
            "organization_name": "Test Org",
            "summary": "Full summary v2",
        }
    }

    with patch("src.chetah.service.df_pdfs", mock_df), patch(
        "src.chetah.service.summaries", ["This is a test summary about disasters."]
    ), patch("src.chetah.service.doc_dict", mock_doc_table):
        yield


def test_chetah_v1_mocked():
    """Happy path for Chetah v1."""
    with patch("src.chetah.service.bm25_v1.transform") as mock_transform:
        mock_transform.return_value = pd.Series([10.0])  # High score for first doc
        response = client.post("/api/v1/products/chetah", json={"query": "disaster"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["title"] == "Test Title 1"


def test_chetah_v1_no_results():
    """Edge case: Chetah v1 finds no matches."""
    with patch("src.chetah.service.bm25_v1.transform") as mock_transform:
        mock_transform.return_value = pd.Series([0.0])  # Score below threshold
        response = client.post("/api/v1/products/chetah", json={"query": "something impossible"})
        assert response.status_code == 200
        assert response.json() == []


def test_chetah_v2_mocked():
    """Happy path for Chetah v2."""
    with patch("src.chetah.service.lemmatize_string") as mock_lem, patch(
        "src.chetah.service.bm25f_v2.calculate_bm25F"
    ) as mock_calc:
        mock_lem.return_value = ["disaster"]
        mock_calc.return_value = [("1", 0.9)]
        response = client.post("/api/v2/products/chetah", json={"query": "humanitarian"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["title"] == "Test Title V2"


def test_chetah_v2_empty_query():
    """Edge case: Empty search query for v2."""
    response = client.post("/api/v2/products/chetah", json={"query": "   "})
    assert response.status_code == 200
    assert response.json() == []


def test_chetah_stress_query():
    """Stress test: Extremely long query string."""
    long_query = "help " * 1000
    with patch("src.chetah.service.bm25_v1.transform") as mock_transform:
        mock_transform.return_value = pd.Series([1.0])
        response = client.post("/api/v1/products/chetah", json={"query": long_query})
        assert response.status_code == 200
