import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_ingest_valid_sensor_payload(client):
    valid_payload_str = json.dumps(
        {
            "device_id": "device-001",
            "metric": "temperature",
            "value": 25.5,
            "unit": "celsius",
        }
    )
    response = client.post(
        "/sensor-readings/ingest",
        json={"payload": valid_payload_str},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "device-001"
    assert data["metric"] == "temperature"
    assert data["value"] == 25.5
    assert data["unit"] == "celsius"
    assert "id" in data
    assert "recorded_at" in data


def test_ingest_invalid_json_payload(client):
    response = client.post(
        "/sensor-readings/ingest",
        json={"payload": "{bad json"},
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_ingest_missing_required_field(client):
    missing_metric_payload = json.dumps(
        {
            "device_id": "device-001",
            "value": 25.5,
        }
    )
    response = client.post(
        "/sensor-readings/ingest",
        json={"payload": missing_metric_payload},
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
