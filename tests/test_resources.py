import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app
from maitri.schemas.resource import ResourceCreate, ResourceUpdate
from maitri.services.resource_service import (
    create_resource,
    get_resource_by_id,
    list_resources_by_station,
    seed_default_resources,
    update_resource,
)
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


@pytest.fixture
def db_session():
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
    try:
        yield db
    finally:
        db.close()


def test_create_valid_resource(client):
    payload = {
        "station_code": "MTR",
        "resource_type": "WATER",
        "current_quantity": 8000.0,
        "capacity": 10000.0,
        "consumption_rate": 200.0,
        "unit": "L",
        "status": "NORMAL",
    }
    response = client.post("/resources/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["resource_type"] == "WATER"
    assert data["current_quantity"] == 8000.0
    assert data["capacity"] == 10000.0
    assert data["consumption_rate"] == 200.0
    assert data["unit"] == "L"
    assert data["status"] == "NORMAL"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_list_maitri_resources(client):
    response = client.get("/stations/MTR/resources")
    assert response.status_code == 200
    resources = response.json()
    assert len(resources) >= 6
    types = {r["resource_type"] for r in resources}
    assert "DIESEL" in types
    assert "BATTERY" in types
    assert "WATER" in types
    assert "FOOD" in types
    assert "MEDICAL" in types
    assert "SPARE_PARTS" in types


def test_list_bharati_resources(client):
    response = client.get("/stations/BHR/resources")
    assert response.status_code == 200
    resources = response.json()
    assert len(resources) >= 6
    types = {r["resource_type"] for r in resources}
    assert "DIESEL" in types
    assert "BATTERY" in types
    assert "WATER" in types
    assert "FOOD" in types
    assert "MEDICAL" in types
    assert "SPARE_PARTS" in types


def test_update_resource_quantity_and_status(client):
    # Fetch Maitri resources
    list_res = client.get("/stations/MTR/resources")
    diesel = next(r for r in list_res.json() if r["resource_type"] == "DIESEL")
    resource_id = diesel["id"]

    # Patch resource
    patch_payload = {
        "current_quantity": 15000.0,
        "status": "WARNING",
        "consumption_rate": 380.0,
    }
    patch_res = client.patch(f"/resources/{resource_id}", json=patch_payload)
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["current_quantity"] == 15000.0
    assert data["status"] == "WARNING"
    assert data["consumption_rate"] == 380.0


def test_invalid_station_resources_404(client):
    res = client.get("/stations/NONEXISTENT/resources")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    post_res = client.post(
        "/resources/",
        json={
            "station_code": "NONEXISTENT",
            "resource_type": "DIESEL",
            "current_quantity": 1000.0,
            "capacity": 2000.0,
            "unit": "L",
        },
    )
    assert post_res.status_code == 404


def test_negative_quantity_rejected(client):
    payload = {
        "station_code": "MTR",
        "resource_type": "DIESEL",
        "current_quantity": -50.0,
        "capacity": 1000.0,
        "unit": "L",
    }
    response = client.post("/resources/", json=payload)
    assert response.status_code == 422  # Pydantic validation error ge=0.0


def test_invalid_capacity_rejected(client):
    payload = {
        "station_code": "MTR",
        "resource_type": "DIESEL",
        "current_quantity": 100.0,
        "capacity": 0.0,
        "unit": "L",
    }
    response = client.post("/resources/", json=payload)
    assert response.status_code == 422  # Pydantic validation error gt=0.0


def test_quantity_exceeds_capacity_rejected(client):
    payload = {
        "station_code": "MTR",
        "resource_type": "DIESEL",
        "current_quantity": 5000.0,
        "capacity": 2000.0,
        "unit": "L",
    }
    response = client.post("/resources/", json=payload)
    assert response.status_code == 400
    assert "exceed" in response.json()["detail"].lower()


def test_invalid_resource_id_patch_404(client):
    response = client.patch(
        "/resources/999999",
        json={"current_quantity": 500.0},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_station_resources_forecast_list(client):
    response = client.get("/stations/MTR/resources/forecast")
    assert response.status_code == 200
    forecasts = response.json()
    assert len(forecasts) >= 6
    for f in forecasts:
        assert "resource_id" in f
        assert "station_id" in f
        assert "resource_type" in f
        assert "current_quantity" in f
        assert "capacity" in f
        assert "consumption_rate" in f
        assert "risk_level" in f
        assert "forecast_message" in f


def test_single_resource_forecast(client):
    list_res = client.get("/stations/MTR/resources")
    diesel = next(r for r in list_res.json() if r["resource_type"] == "DIESEL")
    resource_id = diesel["id"]

    response = client.get(f"/resources/{resource_id}/forecast")
    assert response.status_code == 200
    data = response.json()
    assert data["resource_id"] == resource_id
    assert data["resource_type"] == "DIESEL"
    assert data["estimated_days_remaining"] is not None
    assert data["estimated_hours_remaining"] is not None
    assert data["risk_level"] in ["NORMAL", "LOW", "WARNING", "CRITICAL"]


def test_critical_risk_when_days_remaining_under_two(client):
    # Create a resource with 1.5 days remaining
    res = client.post(
        "/resources/",
        json={
            "station_code": "MTR",
            "resource_type": "WATER",
            "current_quantity": 300.0,
            "capacity": 5000.0,
            "consumption_rate": 200.0,  # 1.5 days
            "unit": "L",
        },
    )
    assert res.status_code == 201
    resource_id = res.json()["id"]

    f_res = client.get(f"/resources/{resource_id}/forecast")
    assert f_res.status_code == 200
    data = f_res.json()
    assert data["estimated_days_remaining"] == 1.5
    assert data["risk_level"] == "CRITICAL"


def test_warning_risk_when_days_remaining_under_seven(client):
    # Create a resource with 5.0 days remaining
    res = client.post(
        "/resources/",
        json={
            "station_code": "MTR",
            "resource_type": "DIESEL",
            "current_quantity": 1000.0,
            "capacity": 5000.0,
            "consumption_rate": 200.0,  # 5.0 days
            "unit": "L",
        },
    )
    assert res.status_code == 201
    resource_id = res.json()["id"]

    f_res = client.get(f"/resources/{resource_id}/forecast")
    assert f_res.status_code == 200
    data = f_res.json()
    assert data["estimated_days_remaining"] == 5.0
    assert data["risk_level"] == "WARNING"


def test_zero_consumption_rate_handled_safely(client):
    # Create a resource with 0 consumption rate
    res = client.post(
        "/resources/",
        json={
            "station_code": "BHR",
            "resource_type": "SPARE_PARTS",
            "current_quantity": 100.0,
            "capacity": 100.0,
            "consumption_rate": 0.0,
            "unit": "units",
        },
    )
    assert res.status_code == 201
    resource_id = res.json()["id"]

    f_res = client.get(f"/resources/{resource_id}/forecast")
    assert f_res.status_code == 200
    data = f_res.json()
    assert data["estimated_days_remaining"] is None
    assert data["estimated_hours_remaining"] is None
    assert data["risk_level"] == "NORMAL"
    assert "zero consumption rate" in data["forecast_message"].lower()


def test_invalid_station_forecast_404(client):
    res = client.get("/stations/NONEXISTENT_STATION/resources/forecast")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_invalid_resource_id_forecast_404(client):
    res = client.get("/resources/999999/forecast")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

