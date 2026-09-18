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


def test_list_stations(client):
    response = client.get("/stations/")
    assert response.status_code == 200
    stations = response.json()
    assert len(stations) >= 2
    codes = [s["station_code"] for s in stations]
    assert "MTR" in codes
    assert "BHR" in codes


def test_get_maitri_station(client):
    # Test lookup by station code
    response_code = client.get("/stations/MTR")
    assert response_code.status_code == 200
    data = response_code.json()
    assert data["station_code"] == "MTR"
    assert data["station_name"] == "Maitri Station"
    assert data["status"] == "ACTIVE"

    # Test lookup by integer id
    st_id = data["id"]
    response_id = client.get(f"/stations/{st_id}")
    assert response_id.status_code == 200
    assert response_id.json()["station_code"] == "MTR"


def test_get_bharati_station(client):
    # Test lookup by station code
    response_code = client.get("/stations/BHR")
    assert response_code.status_code == 200
    data = response_code.json()
    assert data["station_code"] == "BHR"
    assert data["station_name"] == "Bharati Station"
    assert data["status"] == "ACTIVE"

    # Test lookup by integer id
    st_id = data["id"]
    response_id = client.get(f"/stations/{st_id}")
    assert response_id.status_code == 200
    assert response_id.json()["station_code"] == "BHR"


def test_get_sensors_for_maitri(client):
    response = client.get("/stations/MTR/sensors")
    assert response.status_code == 200
    sensors = response.json()
    assert len(sensors) >= 4

    domains = {s["domain"] for s in sensors}
    assert "ENVIRONMENT" in domains
    assert "STRUCTURE" in domains
    assert "ENERGY" in domains
    assert "LOGISTICS" in domains

    sensor_codes = [s["sensor_code"] for s in sensors]
    assert any("MTR-ENV" in c for c in sensor_codes)
    assert any("MTR-ENG" in c for c in sensor_codes)


def test_get_sensors_for_bharati(client):
    response = client.get("/stations/BHR/sensors")
    assert response.status_code == 200
    sensors = response.json()
    assert len(sensors) >= 4

    domains = {s["domain"] for s in sensors}
    assert "ENVIRONMENT" in domains
    assert "STRUCTURE" in domains
    assert "ENERGY" in domains
    assert "LOGISTICS" in domains

    sensor_codes = [s["sensor_code"] for s in sensors]
    assert any("BHR-ENV" in c for c in sensor_codes)
    assert any("BHR-STR" in c for c in sensor_codes)


def test_invalid_station_returns_404(client):
    res_station = client.get("/stations/INVALID_CODE")
    assert res_station.status_code == 404
    assert "not found" in res_station.json()["detail"].lower()

    res_sensors = client.get("/stations/INVALID_CODE/sensors")
    assert res_sensors.status_code == 404
    assert "not found" in res_sensors.json()["detail"].lower()
