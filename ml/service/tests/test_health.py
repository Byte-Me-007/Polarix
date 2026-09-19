"""
Tests for Polarix ML Service Health and Version Routes (SIH26060 - Person C).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ml.service.app import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client: TestClient):
    """Verify health endpoint returns 200 and identifies Polarix ML service."""
    response = client.get("/api/v1/ml/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "polarix-ml"


def test_version_endpoint(client: TestClient):
    """Verify version endpoint returns release metadata and model status."""
    response = client.get("/api/v1/ml/version")
    assert response.status_code == 200
    data = response.json()

    assert data["service_name"] == "polarix-ml-service"
    assert data["contract_version"] == "energy-ml-contract-v1"

    # Sensor models
    assert "maitri" in data["sensor_models"]
    assert data["sensor_models"]["maitri"]["model_version"] == "lstm-ae-v1"
    assert "bharati" in data["sensor_models"]
    assert data["sensor_models"]["bharati"]["model_version"] == "lstm-ae-bharati-v1"

    # Energy models
    assert data["energy_models"]["unified_model_version"] == "energy-ml-v1-candidate"
    assert data["energy_models"]["model_status"] == "CANDIDATE"
    assert data["energy_models"]["forecast_model_version"] == "lstm-energy-baseline-v1"
    assert data["energy_models"]["risk_model_version"] == "energy-deficit-risk-v1"
    assert data["energy_models"]["deficit_risk_threshold"] == 0.35
    assert data["energy_models"]["required_history_hours"] == 24

    # Provenance
    assert data["provenance"]["source"] == "SYNTHETIC_POLARIX_OPERATIONAL_DATA"
    assert "not validated on real classified" in data["provenance"]["disclaimer"].lower()
