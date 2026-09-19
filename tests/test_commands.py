import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app
from maitri.models.alert import Alert
from maitri.models.command import Command
from maitri.schemas.alert import AlertCreate
from maitri.services.alert_service import create_alert
from maitri.services.station_service import seed_default_stations
from maitri.services.sync_service import get_network_status, reset_network_state


@pytest.fixture(autouse=True)
def cleanup_sync():
    reset_network_state()
    yield
    reset_network_state()


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
    try:
        yield db
    finally:
        db.close()


# 1. Create Command Test
def test_create_command(client):
    payload = {
        "command_type": "START_SCENARIO",
        "station_code": "MTR",
        "payload": {"scenario": "STORM"},
    }
    response = client.post("/commands/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["command_type"] == "START_SCENARIO"
    assert data["status"] == "PENDING"
    assert data["station_id"] is not None
    assert data["command_id"].startswith("CMD-")
    assert data["payload"] == {"scenario": "STORM"}
    assert data["result_message"] is None
    assert data["executed_at"] is None


# 2. List Commands Test
def test_list_commands(client):
    client.post(
        "/commands/",
        json={"command_type": "START_SCENARIO", "station_code": "MTR", "payload": {"scenario": "NORMAL_DAY"}},
    )
    client.post(
        "/commands/",
        json={"command_type": "SET_NETWORK_OFFLINE"},
    )
    res = client.get("/commands/")
    assert res.status_code == 200
    cmds = res.json()
    assert len(cmds) >= 2


# 3. Get Command by ID Test
def test_get_command_by_id(client):
    create_res = client.post(
        "/commands/",
        json={"command_id": "CMD-TEST-001", "command_type": "STOP_SCENARIO"},
    )
    assert create_res.status_code == 201
    created = create_res.json()

    # Query by string command_id
    res_str = client.get("/commands/CMD-TEST-001")
    assert res_str.status_code == 200
    assert res_str.json()["command_type"] == "STOP_SCENARIO"

    # Query by integer id
    res_int = client.get(f"/commands/{created['id']}")
    assert res_int.status_code == 200
    assert res_int.json()["command_id"] == "CMD-TEST-001"


# 4. Execute START_SCENARIO Valid Test
def test_execute_start_scenario_valid(client):
    create_res = client.post(
        "/commands/",
        json={
            "command_type": "START_SCENARIO",
            "station_code": "MTR",
            "payload": {"scenario": "STORM"},
        },
    )
    cmd_id = create_res.json()["command_id"]

    exec_res = client.post(f"/commands/{cmd_id}/execute")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "EXECUTED"
    assert "started successfully" in exec_data["result_message"]
    assert exec_data["executed_at"] is not None


# 5. Reject Invalid Scenario Test
def test_reject_invalid_scenario_and_record_failed_status(client):
    create_res = client.post(
        "/commands/",
        json={
            "command_type": "START_SCENARIO",
            "station_code": "MTR",
            "payload": {"scenario": "ALIEN_INVASION"},
        },
    )
    cmd_id = create_res.json()["command_id"]

    exec_res = client.post(f"/commands/{cmd_id}/execute")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "FAILED"
    assert "Unknown scenario" in exec_data["result_message"]
    assert exec_data["executed_at"] is not None


# 6. Execute SET_NETWORK_OFFLINE Test
def test_execute_set_network_offline(client):
    create_res = client.post(
        "/commands/",
        json={"command_type": "SET_NETWORK_OFFLINE"},
    )
    cmd_id = create_res.json()["command_id"]

    exec_res = client.post(f"/commands/{cmd_id}/execute")
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "EXECUTED"
    assert get_network_status() == "OFFLINE"


# 7. Execute SET_NETWORK_ONLINE and REQUEST_SYNC Test
def test_execute_set_network_online_and_request_sync(client):
    # Set offline first and ingest pending telemetry
    client.post("/demo/network/offline")
    client.post(
        "/telemetry/",
        json={"station_code": "MTR", "sensor_code": "MTR-ENV-TMP-01", "value": -19.0},
    )

    # Command: REQUEST_SYNC
    cmd_res = client.post(
        "/commands/",
        json={"command_type": "REQUEST_SYNC"},
    )
    cmd_id = cmd_res.json()["command_id"]

    exec_res = client.post(f"/commands/{cmd_id}/execute")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "EXECUTED"
    assert "Synced 1 pending records" in exec_data["result_message"]
    assert get_network_status() == "ONLINE"


# 8. Execute ACKNOWLEDGE_ALERT Test
def test_execute_acknowledge_alert(client):
    # Create an active alert via client
    alert_res = client.post(
        "/alerts/",
        json={
            "station_code": "MTR",
            "severity": "HIGH",
            "alert_type": "SENSOR_FAULT",
            "title": "Temp probe unstable",
            "message": "Readings noisy",
        },
    )
    assert alert_res.status_code == 201
    alert_id = alert_res.json()["id"]

    # Command to acknowledge
    cmd_res = client.post(
        "/commands/",
        json={
            "command_type": "ACKNOWLEDGE_ALERT",
            "station_code": "MTR",
            "payload": {"alert_id": alert_id},
        },
    )
    cmd_id = cmd_res.json()["command_id"]

    exec_res = client.post(f"/commands/{cmd_id}/execute")
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "EXECUTED"

    # Verify alert status via API
    alert_check = client.get("/stations/MTR/alerts").json()
    ack_alert = next(a for a in alert_check if a["id"] == alert_id)
    assert ack_alert["status"] == "ACKNOWLEDGED"


# 9. Execute RESOLVE_ALERT Test
def test_execute_resolve_alert(client):
    alert_res = client.post(
        "/alerts/",
        json={
            "station_code": "BHR",
            "severity": "MEDIUM",
            "alert_type": "POWER_ANOMALY",
            "title": "Solar array fluctuation",
            "message": "Power output drop",
        },
    )
    assert alert_res.status_code == 201
    alert_id = alert_res.json()["id"]

    cmd_res = client.post(
        "/commands/",
        json={
            "command_type": "RESOLVE_ALERT",
            "station_code": "BHR",
            "payload": {"alert_id": alert_id},
        },
    )
    cmd_id = cmd_res.json()["command_id"]

    exec_res = client.post(f"/commands/{cmd_id}/execute")
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "EXECUTED"

    # Verify alert status
    alert_check = client.get("/stations/BHR/alerts").json()
    res_alert = next(a for a in alert_check if a["id"] == alert_id)
    assert res_alert["status"] == "RESOLVED"



# 10. Invalid Command ID returns 404
def test_invalid_command_id_returns_404(client):
    res_get = client.get("/commands/NON_EXISTENT_CMD")
    assert res_get.status_code == 404

    res_exec = client.post("/commands/NON_EXISTENT_CMD/execute")
    assert res_exec.status_code == 404


# 11. Failed Command Execution Records FAILED Status in DB
def test_failed_command_records_failed_status(client):
    cmd_res = client.post(
        "/commands/",
        json={
            "command_type": "ACKNOWLEDGE_ALERT",
            "payload": {"alert_id": 999999},  # non-existent alert
        },
    )
    cmd_id = cmd_res.json()["command_id"]

    exec_res = client.post(f"/commands/{cmd_id}/execute")
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "FAILED"

    # Verify status in GET
    get_res = client.get(f"/commands/{cmd_id}")
    assert get_res.json()["status"] == "FAILED"
    assert "Execution failed" in get_res.json()["result_message"]
