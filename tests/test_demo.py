import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app
from maitri.services.demo_service import reset_demo_state
from maitri.services.resource_service import seed_default_resources
from maitri.services.station_service import seed_default_stations
from maitri.services.sync_service import reset_network_state


@pytest.fixture(autouse=True)
def cleanup_states():
    reset_network_state()
    reset_demo_state()
    yield
    reset_network_state()
    reset_demo_state()


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


# 1. Starting a valid scenario
def test_start_valid_scenario(client):
    response = client.post("/demo/scenarios/MTR/STORM/start")
    assert response.status_code == 200
    data = response.json()
    assert data["station_code"] == "MTR"
    assert data["scenario_name"] == "STORM"
    assert data["status"] == "RUNNING"
    assert data["is_active"] is True
    assert data["telemetry_generated_count"] == 5
    assert "sync_status" in data
    assert "energy_optimization" in data
    assert "resource_forecast_summary" in data
    assert isinstance(data["resource_forecast_summary"], list)
    assert len(data["resource_forecast_summary"]) >= 1


# 2. Rejecting invalid station
def test_reject_invalid_station(client):
    response = client.post("/demo/scenarios/NON_EXISTENT/STORM/start")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# 3. Rejecting invalid scenario
def test_reject_invalid_scenario(client):
    response = client.post("/demo/scenarios/MTR/ALIEN_INVASION/start")
    assert response.status_code == 400
    assert "unknown scenario" in response.json()["detail"].lower()


# 4. Stopping a scenario
def test_stop_scenario(client):
    # Start scenario first
    client.post("/demo/scenarios/BHR/POWER_CRISIS/start")

    # Stop scenario
    stop_res = client.post("/demo/scenarios/BHR/stop")
    assert stop_res.status_code == 200
    data = stop_res.json()
    assert data["station_code"] == "BHR"
    assert data["is_active"] is False
    assert data["active_scenario"] is None


# 5. Reading scenario status
def test_read_scenario_status(client):
    # Initial status
    res1 = client.get("/demo/scenarios/MTR/status")
    assert res1.status_code == 200
    assert res1.json()["is_active"] is False
    assert res1.json()["active_scenario"] is None

    # Start scenario
    client.post("/demo/scenarios/MTR/NORMAL_DAY/start")

    # Check updated status
    res2 = client.get("/demo/scenarios/MTR/status")
    assert res2.status_code == 200
    assert res2.json()["is_active"] is True
    assert res2.json()["active_scenario"] == "NORMAL_DAY"


# 6. Full sequence returns all phases
def test_full_sequence_returns_all_phases(client):
    response = client.post("/demo/run/full-sequence/MTR")
    assert response.status_code == 200
    data = response.json()
    assert data["station_code"] == "MTR"
    assert data["total_phases"] == 5
    assert len(data["phases"]) == 5

    phase_names = [p["scenario_name"] for p in data["phases"]]
    assert phase_names == [
        "NORMAL_DAY",
        "STORM",
        "POWER_CRISIS",
        "SATELLITE_OUTAGE",
        "RECOVERY",
    ]

    # Verify each phase has required telemetry counts and status details
    for phase in data["phases"]:
        assert phase["telemetry_ingested_count"] == 5
        assert "network_status" in phase
        assert "energy_mode" in phase
        assert "active_alerts_count" in phase


# 7. Satellite outage creates pending sync records
def test_satellite_outage_creates_pending_sync_records(client):
    res = client.post("/demo/scenarios/MTR/SATELLITE_OUTAGE/start")
    assert res.status_code == 200
    data = res.json()
    assert data["sync_status"]["network_status"] == "OFFLINE"
    assert data["sync_status"]["is_online"] is False
    assert data["sync_status"]["pending_count"] >= 5


# 8. Recovery clears pending sync records
def test_recovery_clears_pending_sync_records(client):
    # Outage first
    client.post("/demo/scenarios/BHR/SATELLITE_OUTAGE/start")
    sync_offline = client.get("/sync/status").json()
    assert sync_offline["pending_count"] > 0

    # Recovery
    res_rec = client.post("/demo/scenarios/BHR/RECOVERY/start")
    assert res_rec.status_code == 200
    sync_online = client.get("/sync/status").json()
    assert sync_online["network_status"] == "ONLINE"
    assert sync_online["is_online"] is True
    assert sync_online["pending_count"] == 0


# 9. Alerts are generated during bad / offline conditions
def test_alerts_generated_during_bad_and_failure_conditions(client):
    # SENSOR_FAILURE triggers BAD quality which creates SENSOR_FAULT alert
    res_fail = client.post("/demo/scenarios/MTR/SENSOR_FAILURE/start")
    assert res_fail.status_code == 200
    assert res_fail.json()["active_alerts_count"] >= 1

    alerts_res = client.get("/stations/MTR/alerts")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert any(a["alert_type"] == "SENSOR_FAULT" for a in alerts)


# 10. Response shape includes energy and resource summaries
def test_response_shape_energy_and_resource_summaries(client):
    res = client.post("/demo/scenarios/MTR/NORMAL_DAY/start")
    assert res.status_code == 200
    data = res.json()

    # Energy optimization shape
    energy = data["energy_optimization"]
    assert "current_energy_status" in energy
    assert "recommended_mode" in energy
    assert "actions" in energy
    assert "diesel_reserve_pct" in energy

    # Resource forecast shape
    resources = data["resource_forecast_summary"]
    assert isinstance(resources, list)
    assert len(resources) >= 1
    sample = resources[0]
    assert "resource_type" in sample
    assert "estimated_days_remaining" in sample
    assert "risk_level" in sample
