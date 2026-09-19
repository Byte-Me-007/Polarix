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


def test_device_routes(client):
    device_payload = {
        "device_id": "SN-100",
        "name": "Temp & Pressure Sensor",
        "location": "Station A",
        "status": "active",
    }

    # 1. POST /devices/ creates a device
    res_create = client.post("/devices/", json=device_payload)
    assert res_create.status_code == 201
    created = res_create.json()
    assert created["device_id"] == "SN-100"
    assert created["name"] == "Temp & Pressure Sensor"
    assert "id" in created
    assert "created_at" in created

    # 2. Duplicate POST /devices/ returns 400
    res_dup = client.post("/devices/", json=device_payload)
    assert res_dup.status_code == 400

    # 3. GET /devices/ returns the created device
    res_list = client.get("/devices/")
    assert res_list.status_code == 200
    device_list = res_list.json()
    assert len(device_list) == 1
    assert device_list[0]["device_id"] == "SN-100"

    # 4. GET /devices/{device_id} returns the created device
    res_get = client.get("/devices/SN-100")
    assert res_get.status_code == 200
    assert res_get.json()["device_id"] == "SN-100"

    # 5. GET /devices/missing returns 404
    res_missing = client.get("/devices/missing")
    assert res_missing.status_code == 404


def test_sensor_reading_routes(client):
    reading_1 = {
        "device_id": "SN-100",
        "metric": "temperature",
        "value": -15.4,
        "unit": "C",
    }
    reading_2 = {
        "device_id": "SN-200",
        "metric": "wind_speed",
        "value": 45.2,
        "unit": "km/h",
    }

    # 6. POST /sensor-readings/ creates a reading
    res_create1 = client.post("/sensor-readings/", json=reading_1)
    assert res_create1.status_code == 201
    data1 = res_create1.json()
    assert data1["device_id"] == "SN-100"
    assert data1["metric"] == "temperature"
    assert data1["value"] == -15.4
    assert "id" in data1
    assert "recorded_at" in data1

    res_create2 = client.post("/sensor-readings/", json=reading_2)
    assert res_create2.status_code == 201

    # 7. GET /sensor-readings/ returns readings
    res_list = client.get("/sensor-readings/")
    assert res_list.status_code == 200
    all_readings = res_list.json()
    assert len(all_readings) == 2

    # 8. GET /sensor-readings/device/{device_id} filters readings
    res_filtered = client.get("/sensor-readings/device/SN-100")
    assert res_filtered.status_code == 200
    filtered_readings = res_filtered.json()
    assert len(filtered_readings) == 1
    assert filtered_readings[0]["device_id"] == "SN-100"
    assert filtered_readings[0]["metric"] == "temperature"
