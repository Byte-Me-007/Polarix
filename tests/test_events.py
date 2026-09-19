"""Tests for Unified Events System.

Verifies that:
- Operational events are logged for alerts, commands, and scenario transitions.
- Events are strictly station-isolated.
- High-frequency telemetry ticks do NOT generate events.
"""

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


def test_station_events_endpoint_and_isolation(client):
    """GET /stations/{id}/events returns station-specific events."""
    # Initially empty or nominal
    resp_mtr = client.get("/stations/1/events")
    assert resp_mtr.status_code == 200
    events_mtr_initial = resp_mtr.json()

    resp_bhr = client.get("/stations/2/events")
    assert resp_bhr.status_code == 200
    events_bhr_initial = resp_bhr.json()

    # Trigger scenario on MTR only
    client.post("/demo/scenarios/MTR/STORM/start")

    # MTR should have new operational events
    resp_mtr_after = client.get("/stations/1/events")
    events_mtr_after = resp_mtr_after.json()
    assert len(events_mtr_after) > len(events_mtr_initial)

    # Verify event structure
    first_event = events_mtr_after[0]
    assert "event_id" in first_event
    assert "station_id" in first_event
    assert first_event["station_id"] == 1
    assert "event_type" in first_event
    assert "description" in first_event
    assert "timestamp" in first_event

    # BHR should be completely unaffected (station isolation)
    resp_bhr_after = client.get("/stations/2/events")
    events_bhr_after = resp_bhr_after.json()
    assert len(events_bhr_after) == len(events_bhr_initial)


def test_telemetry_ticks_do_not_create_events(client):
    """Raw telemetry ingestion does NOT create events (keeps event stream clean)."""
    resp_before = client.get("/stations/1/events")
    count_before = len(resp_before.json())

    # Send nominal telemetry observation
    telemetry_payload = {
        "station_code": "MTR",
        "sensor_code": "MTR-ENV-TMP-01",
        "value": -18.5,
        "quality": "GOOD",
    }
    resp = client.post("/telemetry/", json=telemetry_payload)
    assert resp.status_code == 201

    resp_after = client.get("/stations/1/events")
    count_after = len(resp_after.json())

    # Telemetry should NOT increment event log
    assert count_after == count_before


def test_alert_lifecycle_logs_events(client):
    """Alert creation and acknowledgement log operational events."""
    # Send BAD telemetry to trigger alert
    bad_telemetry = {
        "station_code": "MTR",
        "sensor_code": "MTR-ENG-GEN-01",
        "value": 10.0,
        "quality": "BAD",
    }
    client.post("/telemetry/", json=bad_telemetry)

    # Check alert was created
    alerts_resp = client.get("/stations/1/alerts?status=ACTIVE")
    alerts = alerts_resp.json()
    assert len(alerts) > 0
    target_alert = alerts[0]

    # Check that ALERT_TRIGGERED event exists
    events_resp = client.get("/stations/1/events")
    events = events_resp.json()
    event_types = [e["event_type"] for e in events]
    assert "ALERT_TRIGGERED" in event_types

    # Acknowledge alert
    ack_resp = client.post(f"/alerts/{target_alert['id']}/ack")
    assert ack_resp.status_code == 200

    # Check that ALERT_ACKNOWLEDGED event exists
    events_resp2 = client.get("/stations/1/events")
    event_types2 = [e["event_type"] for e in events_resp2.json()]
    assert "ALERT_ACKNOWLEDGED" in event_types2
