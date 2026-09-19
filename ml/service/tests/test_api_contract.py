"""
Automated Contract Consistency Tests for Polarix ML Service (SIH26060 - Person C).

Verifies that live FastAPI service responses strictly conform to the machine-readable
specification defined in ml/service/results/ml_service_api_contract.json to prevent documentation drift.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from ml.energy.tests.fixtures.backend_telemetry_factory import BackendTelemetryFactory
from ml.service.app import create_app
from ml.service.routes.energy import reset_energy_adapter
from ml.service.routes.sensor import reset_sensor_services

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONTRACT_PATH = REPO_ROOT / "ml/service/results/ml_service_api_contract.json"


@pytest.fixture
def contract() -> dict:
    assert CONTRACT_PATH.exists(), f"Contract file not found at {CONTRACT_PATH}"
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def client() -> TestClient:
    reset_energy_adapter()
    reset_sensor_services()
    app = create_app()
    return TestClient(app)


@pytest.fixture
def factory() -> BackendTelemetryFactory:
    return BackendTelemetryFactory(seed=42)


def test_contract_metadata_and_structure(contract: dict):
    """Verify top-level contract metadata fields."""
    assert contract["service_name"] == "polarix-ml"
    assert contract["api_version"] == "v1"
    assert contract["contract_version"] == "ml-service-contract-v1"
    assert set(contract["supported_stations"]) == {"MTR", "BRT"}
    assert "endpoints" in contract
    assert "health_check" in contract["endpoints"]
    assert "version_metadata" in contract["endpoints"]
    assert "sensor_anomaly_analysis" in contract["endpoints"]
    assert "energy_forecasting_and_risk" in contract["endpoints"]


def test_contract_health_endpoint(client: TestClient, contract: dict):
    """Verify health endpoint matches contract schema."""
    ep_spec = contract["endpoints"]["health_check"]
    response = client.get(ep_spec["path"])
    assert response.status_code == ep_spec["response"]["status_code"]

    data = response.json()
    assert data["status"] in ep_spec["response"]["schema"]["status"]["enum"]
    assert data["service"] in ep_spec["response"]["schema"]["service"]["enum"]


def test_contract_version_endpoint(client: TestClient, contract: dict):
    """Verify version endpoint matches contract schema."""
    ep_spec = contract["endpoints"]["version_metadata"]
    response = client.get(ep_spec["path"])
    assert response.status_code == ep_spec["response"]["status_code"]

    data = response.json()
    expected_top_keys = set(ep_spec["response"]["schema"].keys())
    assert set(data.keys()) == expected_top_keys
    assert data["contract_version"] == "energy-ml-contract-v1"
    assert data["energy_models"]["unified_model_version"] == "energy-ml-v1-candidate"
    assert data["energy_models"]["model_status"] == "CANDIDATE"
    assert data["energy_models"]["deficit_risk_threshold"] == 0.35


def test_contract_sensor_endpoint(client: TestClient, contract: dict):
    """Verify sensor analysis endpoint matches contract schema."""
    ep_spec = contract["endpoints"]["sensor_anomaly_analysis"]
    req_example = ep_spec["request"]["example"]

    # Warmup 30 steps to get scored response
    res = None
    for step in range(1, 31):
        payload = {
            "station_id": req_example["station_id"],
            "sensor_id": req_example["sensor_id"],
            "timestamp": f"2026-09-18T12:{step:02d}:00Z",
            "value": req_example["value"] + 0.01 * (step % 3),
            "quality": req_example.get("quality", "GOOD"),
            "unit": req_example.get("unit", "C"),
            "source": req_example.get("source", "SIMULATOR"),
        }
        res = client.post(ep_spec["path"], json=payload)
        assert res.status_code == 200

    assert res is not None
    data = res.json()
    expected_keys = set(ep_spec["response"]["schema"].keys())
    assert set(data.keys()) == expected_keys

    valid_statuses = set(ep_spec["response"]["schema"]["anomaly_status"]["enum"])
    assert data["anomaly_status"] in valid_statuses

    valid_types = set(ep_spec["response"]["schema"]["anomaly_type"]["enum"])
    assert data["anomaly_type"] in valid_types


def test_contract_energy_endpoint(client: TestClient, contract: dict, factory: BackendTelemetryFactory):
    """Verify energy prediction endpoint matches contract schema."""
    ep_spec = contract["endpoints"]["energy_forecasting_and_risk"]

    # 1. Test insufficient history response
    rec_0 = factory.create_record(station_id="MTR", timestamp="2026-09-18T00:00:00Z")
    r0 = client.post(ep_spec["path"], json=rec_0)
    assert r0.status_code == 200
    d0 = r0.json()
    assert d0["status"] == "INSUFFICIENT_HISTORY"
    assert d0["prediction"] is None
    assert d0["required_history"] == 24

    # 2. Feed remaining 23 hours to get prediction available
    stream = factory.create_stream(station_id="MTR", start_time="2026-09-18T01:00:00Z", num_hours=23)
    r_final = None
    for rec in stream:
        r_final = client.post(ep_spec["path"], json=rec)
        assert r_final.status_code == 200

    assert r_final is not None
    d_final = r_final.json()
    assert d_final["status"] == "PREDICTION_AVAILABLE"
    assert d_final["available_history"] == 24

    pred = d_final["prediction"]
    pred_schema = ep_spec["response"]["schema"]["prediction"]["properties"]

    assert pred["contract_version"] == "energy-ml-contract-v1"
    assert pred["model_version"] == "energy-ml-v1-candidate"
    assert pred["forecast_model_version"] == "lstm-energy-baseline-v1"
    assert pred["risk_model_version"] == "energy-deficit-risk-v1"

    # Forecast keys
    expected_forecast_keys = set(pred_schema["forecasts"]["properties"].keys())
    assert set(pred["forecasts"].keys()) == expected_forecast_keys

    # Deficit risk keys
    expected_risk_keys = set(pred_schema["deficit_risk"]["properties"].keys())
    assert set(pred["deficit_risk"].keys()) == expected_risk_keys
    assert pred["deficit_risk"]["threshold"] == 0.35

    # Provenance
    assert pred["provenance"]["model_status"] == "CANDIDATE"
    assert pred["provenance"]["source"] == "SYNTHETIC_POLARIX_OPERATIONAL_DATA"


def test_contract_bhr_rejection(client: TestClient, contract: dict, factory: BackendTelemetryFactory):
    """Verify BHR station rejection matches contract error specification."""
    rec = factory.create_record(station_id="MTR")
    rec["station_id"] = "BHR"

    response = client.post("/api/v1/ml/energy/predict", json=rec)
    assert response.status_code == 400
    assert "Invalid station_id 'BHR'" in response.json()["detail"]
    assert "normalize 'BHR' to 'BRT'" in response.json()["detail"]
