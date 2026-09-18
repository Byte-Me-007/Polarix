import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app
from maitri.services.station_service import seed_default_stations


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

    db = TestingSessionLocal()
    seed_default_stations(db)
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_valid_telemetry_for_maitri(client):
    payload = {
        "station_code": "MTR",
        "sensor_code": "MTR-ENV-TMP-01",
        "value": -18.5,
        "quality": "GOOD",
        "source": "SIMULATOR",
        "anomaly_score": 0.05,
    }
    response = client.post("/telemetry/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["value"] == -18.5
    assert data["quality"] == "GOOD"
    assert data["source"] == "SIMULATOR"
    assert data["unit"] == "°C"
    assert "id" in data
    assert "timestamp" in data


def test_create_valid_telemetry_for_bharati(client):
    payload = {
        "station_code": "BHR",
        "sensor_code": "BHR-ENG-SOL-01",
        "value": 45.2,
        "quality": "GOOD",
        "source": "MQTT",
    }
    response = client.post("/telemetry/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["value"] == 45.2
    assert data["quality"] == "GOOD"
    assert data["source"] == "MQTT"
    assert data["unit"] == "kW"


def test_invalid_station_telemetry(client):
    payload = {
        "station_code": "NON_EXISTENT",
        "sensor_code": "MTR-ENV-TMP-01",
        "value": 10.0,
    }
    response = client.post("/telemetry/", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_invalid_sensor_telemetry(client):
    payload = {
        "station_code": "MTR",
        "sensor_code": "UNKNOWN_SENSOR",
        "value": 10.0,
    }
    response = client.post("/telemetry/", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_sensor_from_wrong_station_rejected(client):
    # Bharati sensor code paired with Maitri station
    payload = {
        "station_code": "MTR",
        "sensor_code": "BHR-ENV-TMP-01",
        "value": 10.0,
    }
    response = client.post("/telemetry/", json=payload)
    assert response.status_code == 400
    assert "does not belong" in response.json()["detail"]


def test_offline_or_unknown_quality_accepted(client):
    payload_offline = {
        "station_code": "MTR",
        "sensor_code": "MTR-ENV-WND-01",
        "value": 0.0,
        "quality": "OFFLINE",
    }
    res1 = client.post("/telemetry/", json=payload_offline)
    assert res1.status_code == 201
    assert res1.json()["quality"] == "OFFLINE"

    payload_unknown = {
        "station_code": "BHR",
        "sensor_code": "BHR-STR-STN-01",
        "value": 120.0,
        "quality": "UNKNOWN",
    }
    res2 = client.post("/telemetry/", json=payload_unknown)
    assert res2.status_code == 201
    assert res2.json()["quality"] == "UNKNOWN"


def test_station_telemetry_history_and_latest(client):
    # Ingest two readings for Maitri temperature sensor
    client.post(
        "/telemetry/",
        json={
            "station_code": "MTR",
            "sensor_code": "MTR-ENV-TMP-01",
            "value": -20.0,
        },
    )
    client.post(
        "/telemetry/",
        json={
            "station_code": "MTR",
            "sensor_code": "MTR-ENV-TMP-01",
            "value": -19.5,
        },
    )
    # Ingest one reading for Maitri generator sensor
    client.post(
        "/telemetry/",
        json={
            "station_code": "MTR",
            "sensor_code": "MTR-ENG-GEN-01",
            "value": 180.0,
        },
    )

    # 1. Test GET /stations/MTR/telemetry
    res_history = client.get("/stations/MTR/telemetry")
    assert res_history.status_code == 200
    history = res_history.json()
    assert len(history) == 3

    # 2. Test GET /stations/MTR/telemetry/latest
    res_latest = client.get("/stations/MTR/telemetry/latest")
    assert res_latest.status_code == 200
    latest = res_latest.json()
    # 2 distinct sensors have telemetry
    assert len(latest) == 2
    # Verify latest value for temp is -19.5
    temp_reading = next(
        (r for r in latest if r["unit"] == "°C" or r["value"] == -19.5), None
    )
    assert temp_reading is not None
    assert temp_reading["value"] == -19.5

    # 3. Test invalid station for telemetry queries
    res_invalid = client.get("/stations/INVALID_STATION/telemetry")
    assert res_invalid.status_code == 404
    res_invalid_latest = client.get("/stations/INVALID_STATION/telemetry/latest")
    assert res_invalid_latest.status_code == 404
