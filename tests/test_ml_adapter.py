"""Tests for ML Integration Adapter and Endpoints.

Verifies that the ML slot is isolated, safe, and returns 'ML INTEGRATION: NOT CONNECTED'
when unavailable, without producing fake anomaly scores or breaking backend services.
"""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.config import Settings
from maitri.database import Base, get_db
from maitri.main import app
from maitri.services.demo_service import reset_demo_state
from maitri.services.ml_adapter import (
    ML_STATUS_CONNECTED,
    ML_STATUS_NOT_CONNECTED,
    MLAdapter,
    ml_adapter,
)
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


def test_ml_adapter_unconfigured_status():
    """When ML_API_URL is empty, adapter reports NOT CONNECTED and no fake results."""
    adapter = MLAdapter(api_url="", api_key="")
    assert not adapter.is_configured
    status = adapter.get_status()
    assert status.status == ML_STATUS_NOT_CONNECTED
    assert status.connected is False
    assert status.ml_api_url is None

    # Test inference dispatch when unconfigured
    result = adapter.send_inference(
        station_id=1,
        timestamp="2026-09-19T12:00:00Z",
        features={"temp": -25.0, "power": 42.0},
    )
    assert result.status == ML_STATUS_NOT_CONNECTED
    assert result.connected is False
    assert result.inference is None
    assert "not configured" in result.error.lower()


def test_ml_adapter_unavailable_network_graceful():
    """When ML API is configured with an unreachable URL, it fails gracefully."""
    adapter = MLAdapter(api_url="http://127.0.0.1:59999", timeout_seconds=0.1)
    assert adapter.is_configured

    status = adapter.get_status()
    assert status.status == ML_STATUS_NOT_CONNECTED
    assert status.connected is False

    # Inference call should catch connection error and never throw
    result = adapter.send_inference(
        station_id=1,
        timestamp="2026-09-19T12:00:00Z",
        features={"temp": -25.0},
    )
    assert result.status == ML_STATUS_NOT_CONNECTED
    assert result.connected is False
    assert result.inference is None
    assert result.error is not None


def test_ml_adapter_successful_mock_inference(monkeypatch):
    """When Person C's API is available, adapter correctly maps request and response."""
    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "model_version": "v1.2.3",
                "anomaly_detected": True,
                "anomaly_score": 0.88,
                "predicted_component": "MTR-ENG-GEN-01",
                "confidence": 0.95,
                "recommendation": "Inspect generator rotor vibration",
            }

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None, headers=None):
            assert "/predict" in url
            assert json["station_id"] == 1
            assert json["features"]["vibration"] == 45.2
            return MockResponse()

    monkeypatch.setattr(httpx, "Client", MockClient)

    adapter = MLAdapter(api_url="http://mock-ml-service:8080", api_key="secret-key")
    result = adapter.send_inference(
        station_id=1,
        timestamp="2026-09-19T12:00:00Z",
        features={"vibration": 45.2},
    )
    assert result.status == ML_STATUS_CONNECTED
    assert result.connected is True
    assert result.inference is not None
    assert result.inference["anomaly_detected"] is True
    assert result.inference["anomaly_score"] == 0.88
    assert result.inference["predicted_component"] == "MTR-ENG-GEN-01"


def test_ml_status_endpoint(client):
    """GET /ml/status returns NOT CONNECTED in default state."""
    response = client.get("/ml/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ML_STATUS_NOT_CONNECTED
    assert data["connected"] is False


def test_ml_contract_endpoint(client):
    """GET /ml/contract returns the placeholder request and response contracts."""
    response = client.get("/ml/contract")
    assert response.status_code == 200
    data = response.json()
    assert "request_schema" in data
    assert "response_schema" in data
    assert "example_request" in data
    assert "example_response" in data
    assert data["example_request"]["station_id"] == 1


def test_ml_infer_endpoint_when_unconnected(client):
    """POST /ml/infer returns NOT CONNECTED and no fake inference when unconfigured."""
    payload = {
        "station_id": 1,
        "timestamp": "2026-09-19T12:00:00Z",
        "features": {"temp": -20.0, "wind": 15.0},
    }
    response = client.post("/ml/infer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ML_STATUS_NOT_CONNECTED
    assert data["connected"] is False
    assert data["inference"] is None


def test_ml_failure_does_not_break_backend(client):
    """Simulate complete ML failure and confirm all backend systems work normally."""
    # Ensure ML adapter points to a failing service
    adapter = MLAdapter(api_url="http://invalid-dead-host-domain:9999", timeout_seconds=0.01)
    result = adapter.send_inference(station_id=1, timestamp="now", features={})
    assert result.connected is False

    # 1. Telemetry history works
    resp = client.get("/stations/1/telemetry")
    assert resp.status_code == 200

    # 2. Energy optimization works
    resp = client.get("/stations/1/energy/optimization")
    assert resp.status_code == 200
    assert "recommended_mode" in resp.json()

    # 3. Logistics & resources work
    resp = client.get("/stations/1/resources")
    assert resp.status_code == 200
    resp = client.get("/stations/1/resources/forecast")
    assert resp.status_code == 200

    # 4. Alerts work
    resp = client.get("/stations/1/alerts")
    assert resp.status_code == 200

    # 5. Station selector works
    resp = client.get("/stations")
    assert resp.status_code == 200

    # 6. Demo scenario works
    resp = client.post("/demo/scenarios/MTR/NORMAL_DAY/start")
    assert resp.status_code == 200
