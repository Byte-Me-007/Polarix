import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app
from maitri.schemas.alert import AlertCreate
from maitri.services.alert_service import (
    acknowledge_alert,
    create_alert,
    get_alert_by_id,
    list_alerts_by_station,
    resolve_alert,
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


def test_create_alert_service(db_session):
    alert_in = AlertCreate(
        station_code="MTR",
        sensor_code="MTR-ENV-TMP-01",
        severity="HIGH",
        alert_type="THRESHOLD_BREACH",
        title="Extreme Cold Alert",
        message="Temperature dropped below -40C",
        anomaly_score=0.92,
    )
    alert = create_alert(db_session, alert_in)
    assert alert.id is not None
    assert alert.severity == "HIGH"
    assert alert.status == "ACTIVE"
    assert alert.alert_type == "THRESHOLD_BREACH"
    assert alert.anomaly_score == 0.92
    assert alert.acknowledged_at is None
    assert alert.resolved_at is None


def test_list_station_alerts_route(client):
    # Create an alert via POST /alerts/
    alert_payload = {
        "station_code": "MTR",
        "sensor_code": "MTR-ENG-GEN-01",
        "severity": "CRITICAL",
        "alert_type": "POWER_ANOMALY",
        "title": "Generator Power Fluctuation",
        "message": "Unstable generator voltage output detected",
    }
    create_res = client.post("/alerts/", json=alert_payload)
    assert create_res.status_code == 201
    created_alert = create_res.json()
    alert_id = created_alert["id"]

    # Query station alerts
    res = client.get("/stations/MTR/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) >= 1
    assert any(a["id"] == alert_id for a in alerts)

    # Query with status filter
    res_active = client.get("/stations/MTR/alerts?status=ACTIVE")
    assert res_active.status_code == 200
    assert any(a["id"] == alert_id for a in res_active.json())


def test_acknowledge_and_resolve_alert_routes(client):
    # Create alert
    alert_payload = {
        "station_code": "BHR",
        "sensor_code": "BHR-LOG-FUL-01",
        "severity": "MEDIUM",
        "alert_type": "FUEL_LEVEL_LOW",
        "title": "Fuel Level Low",
        "message": "Fuel reserve below 25%",
    }
    create_res = client.post("/alerts/", json=alert_payload)
    assert create_res.status_code == 201
    alert_id = create_res.json()["id"]

    # Acknowledge alert
    ack_res = client.post(f"/alerts/{alert_id}/ack")
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["status"] == "ACKNOWLEDGED"
    assert ack_data["acknowledged_at"] is not None

    # Resolve alert
    resolve_res = client.post(f"/alerts/{alert_id}/resolve")
    assert resolve_res.status_code == 200
    resolve_data = resolve_res.json()
    assert resolve_data["status"] == "RESOLVED"
    assert resolve_data["resolved_at"] is not None


def test_invalid_station_alerts_404(client):
    res = client.get("/stations/NONEXISTENT_STATION/alerts")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_invalid_alert_id_ack_and_resolve_404(client):
    ack_res = client.post("/alerts/99999/ack")
    assert ack_res.status_code == 404
    assert "not found" in ack_res.json()["detail"].lower()

    resolve_res = client.post("/alerts/99999/resolve")
    assert resolve_res.status_code == 404
    assert "not found" in resolve_res.json()["detail"].lower()


def test_telemetry_bad_and_offline_creates_alert(client):
    # Ingest BAD telemetry for Bharati sensor
    bad_telemetry = {
        "station_code": "BHR",
        "sensor_code": "BHR-ENV-TMP-01",
        "value": -999.0,
        "quality": "BAD",
        "anomaly_score": 0.99,
    }
    bad_res = client.post("/telemetry/", json=bad_telemetry)
    assert bad_res.status_code == 201

    # Ingest OFFLINE telemetry for Maitri sensor
    offline_telemetry = {
        "station_code": "MTR",
        "sensor_code": "MTR-ENV-WND-01",
        "value": 0.0,
        "quality": "OFFLINE",
    }
    offline_res = client.post("/telemetry/", json=offline_telemetry)
    assert offline_res.status_code == 201

    # Check alerts for Bharati
    bhr_alerts_res = client.get("/stations/BHR/alerts")
    assert bhr_alerts_res.status_code == 200
    bhr_alerts = bhr_alerts_res.json()
    assert any(a["alert_type"] == "SENSOR_FAULT" and a["severity"] == "HIGH" for a in bhr_alerts)

    # Check alerts for Maitri
    mtr_alerts_res = client.get("/stations/MTR/alerts")
    assert mtr_alerts_res.status_code == 200
    mtr_alerts = mtr_alerts_res.json()
    assert any(a["alert_type"] == "SENSOR_OFFLINE" and a["severity"] == "CRITICAL" for a in mtr_alerts)
