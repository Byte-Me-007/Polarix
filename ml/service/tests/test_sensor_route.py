"""
Tests for Polarix ML Service Sensor Analysis Route (SIH26060 - Person C).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ml.service.app import create_app
from ml.service.routes.sensor import reset_sensor_services


@pytest.fixture
def client() -> TestClient:
    reset_sensor_services()
    app = create_app()
    return TestClient(app)


def test_sensor_maitri_warmup_and_steady_state(client: TestClient):
    """Verify Maitri sensor warmup steps (1..29 INSUFFICIENT_DATA) and step 30 NORMAL."""
    for step in range(1, 30):
        rec = {
            "station_id": "MTR",
            "sensor_id": "TEMP_001",
            "timestamp": f"2026-09-18T00:{step:02d}:00Z",
            "value": -15.0 + 0.01 * (step % 3),
            "quality": "GOOD",
            "unit": "C",
            "source": "SIMULATOR",
        }
        response = client.post("/api/v1/ml/sensor/analyze", json=rec)
        assert response.status_code == 200
        data = response.json()
        assert data["anomaly_status"] == "INSUFFICIENT_DATA"
        assert data["anomaly_score"] is None
        assert data["station_id"] == "MTR"
        assert data["sensor_id"] == "TEMP_001"

    # Step 30
    rec_30 = {
        "station_id": "MTR",
        "sensor_id": "TEMP_001",
        "timestamp": "2026-09-18T00:30:00Z",
        "value": -15.0,
        "quality": "GOOD",
        "unit": "C",
        "source": "SIMULATOR",
    }
    response_30 = client.post("/api/v1/ml/sensor/analyze", json=rec_30)
    assert response_30.status_code == 200
    data_30 = response_30.json()
    assert data_30["anomaly_status"] == "NORMAL"
    assert data_30["anomaly_type"] == "NORMAL"
    assert isinstance(data_30["anomaly_score"], float)
    assert data_30["model_version"] == "lstm-ae-v1"


def test_sensor_spike_anomaly_classification(client: TestClient):
    """Verify sudden extreme value shift triggers ANOMALY status and SPIKE type."""
    # Warmup 29 steps
    for step in range(1, 30):
        client.post(
            "/api/v1/ml/sensor/analyze",
            json={
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": f"2026-09-18T01:{step:02d}:00Z",
                "value": -15.0,
            },
        )

    # 30th point is a shock spike (+50 deg C)
    res = client.post(
        "/api/v1/ml/sensor/analyze",
        json={
            "station_id": "MTR",
            "sensor_id": "TEMP_001",
            "timestamp": "2026-09-18T01:30:00Z",
            "value": 50.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["anomaly_status"] == "ANOMALY"
    assert data["anomaly_type"] == "SPIKE"
    assert data["anomaly_score"] > 0.017674  # Exceeds Maitri frozen threshold


def test_sensor_bharati_steady_state(client: TestClient):
    """Verify Bharati station sensor anomaly pipeline execution."""
    for step in range(1, 31):
        res = client.post(
            "/api/v1/ml/sensor/analyze",
            json={
                "station_id": "BRT",
                "sensor_id": "BRT_TEMP_001",
                "timestamp": f"2026-09-18T02:{step:02d}:00Z",
                "value": -10.0 + 0.01 * (step % 3),
            },
        )
        assert res.status_code == 200

    data = res.json()
    assert data["station_id"] == "BRT"
    assert data["anomaly_status"] == "NORMAL"
    assert data["anomaly_type"] == "NORMAL"
    assert data["model_version"] == "lstm-ae-bharati-v1"


def test_sensor_bhr_station_id_rejected(client: TestClient):
    """Verify BHR station code is rejected with HTTP 400 and normalization requirement."""
    res = client.post(
        "/api/v1/ml/sensor/analyze",
        json={
            "station_id": "BHR",
            "sensor_id": "TEMP_001",
            "timestamp": "2026-09-18T03:00:00Z",
            "value": -15.0,
        },
    )
    assert res.status_code == 400
    assert "Invalid station_id 'BHR'" in res.json()["detail"]
    assert "normalize 'BHR' to 'BRT'" in res.json()["detail"]


def test_sensor_duplicate_and_stale_rejected(client: TestClient):
    """Verify duplicate and stale timestamps return HTTP 400."""
    rec = {
        "station_id": "MTR",
        "sensor_id": "VIB_001",
        "timestamp": "2026-09-18T04:10:00Z",
        "value": 0.85,
    }
    r1 = client.post("/api/v1/ml/sensor/analyze", json=rec)
    assert r1.status_code == 200

    # Duplicate
    r2 = client.post("/api/v1/ml/sensor/analyze", json=rec)
    assert r2.status_code == 400
    assert "Duplicate timestamp" in r2.json()["detail"]

    # Stale
    rec_stale = {
        "station_id": "MTR",
        "sensor_id": "VIB_001",
        "timestamp": "2026-09-18T04:09:00Z",
        "value": 0.85,
    }
    r3 = client.post("/api/v1/ml/sensor/analyze", json=rec_stale)
    assert r3.status_code == 400
    assert "Out-of-order" in r3.json()["detail"] or "Stale" in r3.json()["detail"]
