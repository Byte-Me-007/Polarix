import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app
from maitri.models.alert import Alert
from maitri.models.telemetry import Telemetry
from maitri.services.station_service import seed_default_stations
from maitri.services.sync_service import (
    get_network_status,
    reset_network_state,
    set_network_offline,
    set_network_online_and_sync,
)
from maitri.simulator import generate_telemetry_batch


@pytest.fixture(autouse=True)
def cleanup_sync_state():
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


def test_default_sync_status_is_online(client):
    response = client.get("/sync/status")
    assert response.status_code == 200
    data = response.json()
    assert data["network_status"] == "ONLINE"
    assert data["is_online"] is True
    assert data["pending_count"] == 0
    assert data["synced_count"] == 0
    assert data["total_count"] == 0


def test_switching_network_offline(client):
    response = client.post("/demo/network/offline")
    assert response.status_code == 200
    data = response.json()
    assert data["network_status"] == "OFFLINE"
    assert data["is_online"] is False
    assert get_network_status() == "OFFLINE"

    # Verify /sync/status reflects OFFLINE
    status_res = client.get("/sync/status")
    assert status_res.status_code == 200
    assert status_res.json()["network_status"] == "OFFLINE"
    assert status_res.json()["is_online"] is False


def test_switching_network_online(client):
    # Switch offline first
    client.post("/demo/network/offline")
    assert get_network_status() == "OFFLINE"

    # Switch back online
    response = client.post("/demo/network/online")
    assert response.status_code == 200
    data = response.json()
    assert data["network_status"] == "ONLINE"
    assert data["is_online"] is True
    assert get_network_status() == "ONLINE"


def test_telemetry_queued_while_offline_and_pending_count(client):
    # Switch to offline mode
    client.post("/demo/network/offline")

    # Ingest 3 telemetry readings
    t1 = {
        "station_code": "MTR",
        "sensor_code": "MTR-ENV-TMP-01",
        "value": -22.0,
        "quality": "GOOD",
    }
    t2 = {
        "station_code": "MTR",
        "sensor_code": "MTR-ENV-WND-01",
        "value": 15.0,
        "quality": "GOOD",
    }
    t3 = {
        "station_code": "BHR",
        "sensor_code": "BHR-ENV-TMP-01",
        "value": -14.0,
        "quality": "GOOD",
    }
    for payload in (t1, t2, t3):
        res = client.post("/telemetry/", json=payload)
        assert res.status_code == 201

    # Check /sync/status
    status_res = client.get("/sync/status")
    assert status_res.status_code == 200
    stats = status_res.json()
    assert stats["network_status"] == "OFFLINE"
    assert stats["is_online"] is False
    assert stats["pending_count"] == 3
    assert stats["synced_count"] == 0
    assert stats["total_count"] == 3


def test_recovery_sync_clears_pending_queue(client):
    # Queue records while offline
    client.post("/demo/network/offline")
    client.post(
        "/telemetry/",
        json={
            "station_code": "MTR",
            "sensor_code": "MTR-ENV-TMP-01",
            "value": -20.5,
        },
    )
    client.post(
        "/telemetry/",
        json={
            "station_code": "MTR",
            "sensor_code": "MTR-ENG-GEN-01",
            "value": 185.0,
        },
    )

    # Verify 2 pending
    stats_offline = client.get("/sync/status").json()
    assert stats_offline["pending_count"] == 2
    assert stats_offline["synced_count"] == 0

    # Recover to online
    sync_res = client.post("/demo/network/online")
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["network_status"] == "ONLINE"
    assert sync_data["is_online"] is True
    assert sync_data["synced_now"] == 2
    assert sync_data["pending_count"] == 0
    assert sync_data["synced_count"] == 2

    # Status route verification
    stats_online = client.get("/sync/status").json()
    assert stats_online["pending_count"] == 0
    assert stats_online["synced_count"] == 2
    assert stats_online["total_count"] == 2
    assert stats_online["last_sync_timestamp"] is not None


def test_satellite_outage_simulator_telemetry_queueing(client):
    # Online mode, but SATELLITE_OUTAGE simulation marks telemetry as unsynced
    outage_batch = generate_telemetry_batch("MTR", scenario="SATELLITE_OUTAGE")
    for record in outage_batch:
        res = client.post(
            "/telemetry/",
            json={
                "station_code": record["station_code"],
                "sensor_code": record["sensor_code"],
                "value": record["value"],
                "quality": record["quality"],
                "source": "SIMULATOR",
                "synced": record["synced"],
            },
        )
        assert res.status_code == 201

    stats = client.get("/sync/status").json()
    assert stats["network_status"] == "ONLINE"
    assert stats["pending_count"] == len(outage_batch)

    # Sync through recovery
    reconcile_res = client.post("/demo/network/online")
    assert reconcile_res.status_code == 200
    assert reconcile_res.json()["pending_count"] == 0
    assert reconcile_res.json()["synced_count"] == len(outage_batch)


def test_bad_and_offline_telemetry_triggers_alerts_while_offline(client, db_session):
    client.post("/demo/network/offline")

    # Ingest BAD quality telemetry
    bad_payload = {
        "station_code": "MTR",
        "sensor_code": "MTR-ENG-GEN-01",
        "value": 15.0,
        "quality": "BAD",
        "anomaly_score": 0.95,
    }
    res_bad = client.post("/telemetry/", json=bad_payload)
    assert res_bad.status_code == 201

    # Ingest OFFLINE quality telemetry
    offline_payload = {
        "station_code": "MTR",
        "sensor_code": "MTR-STR-VIB-01",
        "value": 0.0,
        "quality": "OFFLINE",
        "anomaly_score": 1.0,
    }
    res_offline = client.post("/telemetry/", json=offline_payload)
    assert res_offline.status_code == 201

    # Alerts route check
    alerts_res = client.get("/stations/MTR/alerts")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert len(alerts) == 2

    fault_alert = next((a for a in alerts if a["alert_type"] == "SENSOR_FAULT"), None)
    assert fault_alert is not None
    assert fault_alert["severity"] == "HIGH"

    offline_alert = next((a for a in alerts if a["alert_type"] == "SENSOR_OFFLINE"), None)
    assert offline_alert is not None
    assert offline_alert["severity"] == "CRITICAL"


def test_invalid_telemetry_rejected_while_offline(client):
    client.post("/demo/network/offline")

    # Invalid station
    res_station = client.post(
        "/telemetry/",
        json={
            "station_code": "INVALID_STATION",
            "sensor_code": "MTR-ENV-TMP-01",
            "value": 10.0,
        },
    )
    assert res_station.status_code == 404

    # Invalid sensor
    res_sensor = client.post(
        "/telemetry/",
        json={
            "station_code": "MTR",
            "sensor_code": "UNKNOWN_SENSOR",
            "value": 10.0,
        },
    )
    assert res_sensor.status_code == 404
