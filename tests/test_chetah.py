from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_chetah_v1():
    response = client.post(
        "/api/v1/products/chetah",
        json={"query": "disaster"}
    )
    assert response.status_code == 200
    assert "results" in response.json()
    assert len(response.json()["results"]) <= 10

def test_chetah_v2():
    response = client.post(
        "/api/v2/products/chetah",
        json={"query": "humanitarian"}
    )
    assert response.status_code == 200
    assert "results" in response.json()
    assert len(response.json()["results"]) <= 10
