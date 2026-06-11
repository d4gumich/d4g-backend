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
    # Mock the lazy-loading functions in the service module
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
            "Title": "Test Title V2",
            "report_title": "Test Title V2",
            "doc_creation_date": "2023-01-01",
            "URL": "http://testv2.com",
            "organization_name": "Test Org",
            "summary": "Full summary v2",
        }
    }

    mock_inv_index = {
        "term_ids": {"disaster": "101"},
        "inv_index": {"101": {"fields": {}}},
        "corpus_prop": {
            "number_of_doc_corpus": 1,
            "content_avdl": 10,
            "metadata_avdl": 5,
        },
    }

    mock_bm25_v1 = MagicMock()
    mock_bm25f_v2 = MagicMock()

    with (
        patch("src.chetah.service.get_chetah_v1_data") as mock_v1,
        patch("src.chetah.service.get_chetah_v2_data") as mock_v2,
    ):
        mock_v1.return_value = (mock_df, ["This is a test summary about disasters."], mock_bm25_v1)
        mock_v2.return_value = (mock_inv_index, mock_doc_table, mock_bm25f_v2)
        yield {
            "v1_bm25": mock_bm25_v1,
            "v2_bm25f": mock_bm25f_v2,
        }


def test_chetah_v1_mocked(mock_chetah_data):
    """Happy path for Chetah v1."""
    mock_chetah_data["v1_bm25"].transform.return_value = pd.Series([10.0])  # High score for first doc
    response = client.post("/api/v1/products/chetah", json={"query": "disaster"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["title"] == "Test Title 1"


def test_chetah_v1_no_results(mock_chetah_data):
    """Edge case: Chetah v1 finds no matches."""
    mock_chetah_data["v1_bm25"].transform.return_value = pd.Series([0.0])  # Score below threshold
    response = client.post("/api/v1/products/chetah", json={"query": "something impossible"})
    assert response.status_code == 200
    assert response.json() == []


def test_chetah_v2_mocked(mock_chetah_data):
    """Happy path for Chetah v2."""
    with patch("src.chetah.service.lemmatize_string") as mock_lem:
        mock_lem.return_value = ["disaster"]
        mock_chetah_data["v2_bm25f"].calculate_bm25F.return_value = [("1", 0.9)]
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


def test_chetah_stress_query(mock_chetah_data):
    """Stress test: Extremely long query string."""
    long_query = "help " * 1000
    mock_chetah_data["v1_bm25"].transform.return_value = pd.Series([1.0])
    response = client.post("/api/v1/products/chetah", json={"query": long_query})
    assert response.status_code == 200
