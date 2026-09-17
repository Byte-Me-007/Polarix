from fastapi.testclient import TestClient

from bharati.main import app

client = TestClient(app)


def test_bharati_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("service") == "bharati"
    assert data.get("status") == "running"


def test_bharati_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert data.get("service") == "bharati"
