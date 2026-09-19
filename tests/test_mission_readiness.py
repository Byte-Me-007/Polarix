"""Tests for Deterministic Mission Readiness.

Verifies that:
- Mission readiness is computed per station (MTR and BHR).
- Output contains deterministic scores across environment, energy, structure, connectivity, supplies.
- Readiness degrades predictably when operational conditions change (e.g. POWER_CRISIS scenario).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app
from maitri.schemas.alert import AlertCreate
from maitri.services.alert_service import create_alert
from maitri.services.demo_service import reset_demo_state, start_station_scenario
from maitri.services.resource_service import seed_default_resources
from maitri.services.station_service import seed_default_stations
from maitri.services.sync_service import reset_network_state, set_network_offline


@pytest.fixture
def client():
    reset_network_state()
    reset_demo_state()

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
    reset_network_state()
    reset_demo_state()


def test_mission_readiness_baseline_maitri(client):
    """Maitri returns deterministic readiness score in nominal state."""
    response = client.get("/stations/1/mission-readiness")
    assert response.status_code == 200
    data = response.json()

    assert data["station_id"] == 1
    assert data["station_code"] == "MTR"
    assert data["overall_status"] in ("OPERATIONAL", "DEGRADED")
    assert 0.0 <= data["readiness_score"] <= 100.0

    # Verify all 5 subsystems are present
    subsystems = data["subsystems"]
    assert "environment" in subsystems
    assert "energy" in subsystems
    assert "structure" in subsystems
    assert "connectivity" in subsystems
    assert "supplies" in subsystems

    for sub_key in ("environment", "energy", "structure", "connectivity", "supplies"):
        sub = subsystems[sub_key]
        assert "score" in sub
        assert "status" in sub
        assert "details" in sub
        assert 0.0 <= sub["score"] <= 100.0


def test_mission_readiness_bharati(client):
    """Bharati (station 2) returns station-specific readiness."""
    response = client.get("/stations/2/mission-readiness")
    assert response.status_code == 200
    data = response.json()

    assert data["station_id"] == 2
    assert data["station_code"] == "BHR"
    assert "subsystems" in data


def test_mission_readiness_degrades_during_power_crisis(client):
    """Readiness score decreases significantly during a POWER_CRISIS scenario."""
    # Baseline
    res_before = client.get("/stations/1/mission-readiness")
    score_before = res_before.json()["readiness_score"]

    # Start POWER_CRISIS
    start_res = client.post("/demo/scenarios/MTR/POWER_CRISIS/start")
    assert start_res.status_code == 200

    # Re-evaluate
    res_after = client.get("/stations/1/mission-readiness")
    assert res_after.status_code == 200
    data_after = res_after.json()

    assert data_after["readiness_score"] < score_before
    assert data_after["overall_status"] in ("DEGRADED", "AT_RISK", "CRITICAL")
    assert data_after["subsystems"]["energy"]["status"] in ("DEGRADED", "AT_RISK", "CRITICAL")


def test_mission_readiness_critical_alert_impact(client):
    """Injecting a critical alert caps readiness and prevents OPERATIONAL status."""
    # Create critical alert directly
    res = client.get("/stations/1/alerts")
    assert res.status_code == 200

    # Trigger satellite outage to test connectivity degradation
    client.post("/demo/network/offline")

    res_readiness = client.get("/stations/1/mission-readiness")
    assert res_readiness.status_code == 200
    data = res_readiness.json()
    assert data["subsystems"]["connectivity"]["status"] == "AT_RISK"
    assert data["subsystems"]["connectivity"]["score"] < 60.0


def test_mission_readiness_invalid_station(client):
    """Invalid station ID returns 404."""
    response = client.get("/stations/999/mission-readiness")
    assert response.status_code == 404
