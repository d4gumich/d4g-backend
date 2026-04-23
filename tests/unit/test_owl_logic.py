import numpy as np
import pytest

from src.owl.service import OwlService


def test_l2_normalize():
    service = OwlService()
    v = np.array([3.0, 4.0])
    normalized = service._l2_normalize(v)

    # Magnitude should be 1
    mag = np.linalg.norm(normalized)
    assert pytest.approx(mag) == 1.0
    # Values should be 0.6 and 0.8
    assert normalized[0] == 0.6
    assert normalized[1] == 0.8


def test_coerce_doc_for_context():
    service = OwlService()
    raw_row = {
        "title": "Report A",
        "organization_name": "UN",
        "combined_details": "Details here",
        "URL": "http://test.com",
        "similarity": 0.95,
    }
    coerced = service._coerce_doc_for_context(raw_row)

    assert coerced["title"] == "Report A"
    assert coerced["source"] == "UN"
    assert coerced["combined_details"] == "Details here"


def test_build_prompt():
    service = OwlService()
    docs = [
        {"title": "Doc 1", "source": "Org 1", "combined_details": "Content 1"},
        {"title": "Doc 2", "source": "Org 2", "combined_details": "Content 2"},
    ]
    prompt = service._build_prompt("What is happening?", docs)

    assert "### User question\nWhat is happening?" in prompt
    assert "Doc 1" in prompt
    assert "Doc 2" in prompt
    assert "Content 1" in prompt
