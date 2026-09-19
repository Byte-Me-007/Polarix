"""
Tests for Polarix ML Service Energy Prediction Route (SIH26060 - Person C).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from ml.energy.tests.fixtures.backend_telemetry_factory import BackendTelemetryFactory
from ml.service.app import create_app
from ml.service.routes.energy import reset_energy_adapter


@pytest.fixture
def factory() -> BackendTelemetryFactory:
    return BackendTelemetryFactory(seed=42)


@pytest.fixture
def client() -> TestClient:
    reset_energy_adapter()
    app = create_app()
    return TestClient(app)


def test_energy_insufficient_history_warmup(client: TestClient, factory: BackendTelemetryFactory):
    """Verify first 23 hourly records return INSUFFICIENT_HISTORY status with null prediction."""
    stream = factory.create_stream(station_id="MTR", num_hours=23)
    for i, rec in enumerate(stream):
        response = client.post("/api/v1/ml/energy/predict", json=rec)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "INSUFFICIENT_HISTORY"
        assert data["station_id"] == "MTR"
        assert data["available_history"] == (i + 1)
        assert data["required_history"] == 24
        assert data["prediction"] is None


def test_energy_prediction_available_on_24th_record(client: TestClient, factory: BackendTelemetryFactory):
    """Verify 24th contiguous record returns PREDICTION_AVAILABLE with unified payload."""
    stream = factory.create_stream(station_id="MTR", num_hours=24)
    res_data = None
    for rec in stream:
        response = client.post("/api/v1/ml/energy/predict", json=rec)
        assert response.status_code == 200
        res_data = response.json()

    assert res_data is not None
    assert res_data["status"] == "PREDICTION_AVAILABLE"
    assert res_data["available_history"] == 24
    assert res_data["prediction"] is not None

    pred = res_data["prediction"]
    assert pred["station_id"] == "MTR"
    assert pred["contract_version"] == "energy-ml-contract-v1"
    assert pred["model_version"] == "energy-ml-v1-candidate"
    assert pred["forecast_model_version"] == "lstm-energy-baseline-v1"
    assert pred["risk_model_version"] == "energy-deficit-risk-v1"

    # Forecasts
    assert math.isfinite(pred["forecasts"]["power_demand_1h_kw"])
    assert math.isfinite(pred["forecasts"]["battery_soc_1h_percent"])
    assert math.isfinite(pred["forecasts"]["energy_demand_6h_kwh"])
    assert math.isfinite(pred["forecasts"]["energy_demand_24h_kwh"])

    # Deficit risk
    assert 0.0 <= pred["deficit_risk"]["probability"] <= 1.0
    assert isinstance(pred["deficit_risk"]["decision"], bool)
    assert pred["deficit_risk"]["threshold"] == 0.35

    # Provenance
    assert pred["provenance"]["model_status"] == "CANDIDATE"
    assert pred["provenance"]["source"] == "SYNTHETIC_POLARIX_OPERATIONAL_DATA"


def test_energy_station_isolation_mtr_and_brt(client: TestClient, factory: BackendTelemetryFactory):
    """Verify interleaving MTR and BRT streams maintains independent 24h buffers."""
    mtr_stream = factory.create_stream(station_id="MTR", num_hours=24)
    brt_stream = factory.create_stream(station_id="BRT", num_hours=24)

    for i in range(24):
        r_mtr = client.post("/api/v1/ml/energy/predict", json=mtr_stream[i])
        r_brt = client.post("/api/v1/ml/energy/predict", json=brt_stream[i])
        assert r_mtr.status_code == 200
        assert r_brt.status_code == 200

        d_mtr = r_mtr.json()
        d_brt = r_brt.json()

        if i < 23:
            assert d_mtr["status"] == "INSUFFICIENT_HISTORY"
            assert d_brt["status"] == "INSUFFICIENT_HISTORY"
        else:
            assert d_mtr["status"] == "PREDICTION_AVAILABLE"
            assert d_brt["status"] == "PREDICTION_AVAILABLE"
            assert d_mtr["prediction"]["station_id"] == "MTR"
            assert d_brt["prediction"]["station_id"] == "BRT"


def test_energy_bhr_station_id_rejected(client: TestClient, factory: BackendTelemetryFactory):
    """Verify BHR station code is rejected with HTTP 400 and explicit normalization requirement."""
    rec = factory.create_record(station_id="MTR")
    rec["station_id"] = "BHR"

    response = client.post("/api/v1/ml/energy/predict", json=rec)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Invalid station_id 'BHR'" in detail
    assert "normalize 'BHR' to 'BRT'" in detail


def test_energy_duplicate_and_out_of_order_rejected(client: TestClient, factory: BackendTelemetryFactory):
    """Verify duplicate and out-of-order timestamps return HTTP 400."""
    rec1 = factory.create_record(station_id="MTR", timestamp="2026-09-18T10:00:00Z")
    rec2_dup = factory.create_record(station_id="MTR", timestamp="2026-09-18T10:00:00Z")
    rec3_stale = factory.create_record(station_id="MTR", timestamp="2026-09-18T09:00:00Z")

    # Ingest rec1
    r1 = client.post("/api/v1/ml/energy/predict", json=rec1)
    assert r1.status_code == 200

    # Ingest duplicate
    r2 = client.post("/api/v1/ml/energy/predict", json=rec2_dup)
    assert r2.status_code == 400
    assert "Duplicate telemetry timestamp" in r2.json()["detail"]

    # Ingest out-of-order
    r3 = client.post("/api/v1/ml/energy/predict", json=rec3_stale)
    assert r3.status_code == 400
    assert "Out-of-order telemetry" in r3.json()["detail"]


def test_energy_gap_resets_contiguous_history(client: TestClient, factory: BackendTelemetryFactory):
    """Verify timeline gaps reset contiguous window counter without fabricating data."""
    start_dt = datetime(2026, 9, 18, 0, 0, 0, tzinfo=timezone.utc)
    stream_part1 = factory.create_stream(station_id="MTR", start_time=start_dt, num_hours=12)
    for rec in stream_part1:
        client.post("/api/v1/ml/energy/predict", json=rec)

    # 4-hour gap: jump to hour 16
    gap_dt = start_dt + timedelta(hours=16)
    stream_part2 = factory.create_stream(station_id="MTR", start_time=gap_dt, num_hours=12)
    for rec in stream_part2:
        r = client.post("/api/v1/ml/energy/predict", json=rec)
        assert r.status_code == 200
        # Even with 24 total records received, contiguous suffix is only 12 -> INSUFFICIENT_HISTORY
        assert r.json()["status"] == "INSUFFICIENT_HISTORY"


def test_energy_missing_required_field_rejected(client: TestClient, factory: BackendTelemetryFactory):
    """Verify missing required physical fields return HTTP 422 Unprocessable Entity."""
    rec = factory.create_record(station_id="MTR")
    del rec["power_demand_kw"]

    response = client.post("/api/v1/ml/energy/predict", json=rec)
    assert response.status_code == 422
