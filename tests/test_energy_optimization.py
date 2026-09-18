import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app
from maitri.models.resource import Resource
from maitri.services.resource_service import seed_default_resources
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
    seed_default_resources(db)
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


def test_energy_optimization_response_shape(client):
    response = client.get("/stations/MTR/energy/optimization")
    assert response.status_code == 200
    data = response.json()

    assert "station_id" in data
    assert "current_energy_status" in data
    assert "risk_level" in data
    assert "recommended_mode" in data
    assert "actions" in data
    assert "reason" in data
    assert isinstance(data["actions"], list)
    assert len(data["actions"]) > 0


def test_normal_energy_status_default(client):
    response = client.get("/stations/MTR/energy/optimization")
    assert response.status_code == 200
    data = response.json()

    assert data["current_energy_status"] == "OPTIMAL"
    assert data["risk_level"] == "NORMAL"
    assert data["recommended_mode"] == "STANDARD_BALANCED"
    assert "nominal" in data["reason"].lower()


def test_warning_energy_status_fuel_conservation(client):
    # Fetch resources to find diesel ID for Maitri
    list_res = client.get("/stations/MTR/resources")
    diesel = next(r for r in list_res.json() if r["resource_type"] == "DIESEL")
    resource_id = diesel["id"]

    # Patch diesel to 25% capacity (15,000L out of 60,000L)
    patch_res = client.patch(
        f"/resources/{resource_id}",
        json={"current_quantity": 15000.0, "status": "WARNING"},
    )
    assert patch_res.status_code == 200


    response = client.get("/stations/MTR/energy/optimization")
    assert response.status_code == 200
    data = response.json()

    assert data["current_energy_status"] == "DEGRADED"
    assert data["risk_level"] == "WARNING"
    assert data["recommended_mode"] == "FUEL_CONSERVATION"
    assert any("reduce generator" in a.lower() or "throttle" in a.lower() for a in data["actions"])


def test_critical_power_crisis_status(client):
    # Fetch resources to find diesel ID for Maitri
    list_res = client.get("/stations/MTR/resources")
    diesel = next(r for r in list_res.json() if r["resource_type"] == "DIESEL")
    resource_id = diesel["id"]

    # Patch diesel to 1 day remaining (e.g., 350L at 350L/day)
    client.patch(
        f"/resources/{resource_id}",
        json={"current_quantity": 350.0, "status": "CRITICAL"},
    )

    response = client.get("/stations/MTR/energy/optimization")
    assert response.status_code == 200
    data = response.json()

    assert data["current_energy_status"] == "CRITICAL"
    assert data["risk_level"] == "CRITICAL"
    assert data["recommended_mode"] == "POWER_CRISIS_MINIMAL"
    assert any("shed non-critical" in a.lower() for a in data["actions"])


def test_solar_priority_mode_when_solar_available(client):
    # Ingest high solar output for Bharati solar sensor (BHR-ENG-SOL-01)
    solar_telemetry = {
        "station_code": "BHR",
        "sensor_code": "BHR-ENG-SOL-01",
        "value": 48.5,
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    t_res = client.post("/telemetry/", json=solar_telemetry)
    assert t_res.status_code == 201

    response = client.get("/stations/BHR/energy/optimization")
    assert response.status_code == 200
    data = response.json()

    assert data["current_energy_status"] == "OPTIMAL"
    assert data["risk_level"] == "NORMAL"
    assert data["recommended_mode"] == "SOLAR_PRIORITY"
    assert data["solar_output_kw"] == 48.5
    assert any("solar" in a.lower() for a in data["actions"])


def test_invalid_station_energy_optimization_404(client):
    response = client.get("/stations/NONEXISTENT_STATION/energy/optimization")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
