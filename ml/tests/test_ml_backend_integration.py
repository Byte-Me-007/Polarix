"""Integration Regression Tests for Polarix ML <-> Backend Contract Boundary.

Step 43: Validate that the ML subsystem safely consumes backend-style telemetry
and returns canonical 11-field contracts across all operational scenarios.
"""

from __future__ import annotations

import json
import math
import pytest
from datetime import datetime, timezone, timedelta

from ml.inference.maitri_backend_contract import (
    adapt_backend_input as adapt_mtr_input,
    adapt_backend_output as adapt_mtr_output,
    process_backend_payload as process_mtr_payload,
)
from ml.inference.bharati_backend_contract import (
    adapt_backend_input as adapt_brt_input,
    adapt_backend_output as adapt_brt_output,
    process_backend_payload as process_brt_payload,
)
from ml.inference.inference_contract import (
    TelemetryInput as MaitriTelemetryInput,
    InvalidContractError as MaitriInvalidContractError,
    DuplicateTelemetryError as MaitriDuplicateError,
    StaleTelemetryError as MaitriStaleError,
)
from ml.inference.bharati_inference_contract import (
    BharatiTelemetryInput,
    InvalidContractError as BharatiInvalidContractError,
    DuplicateTelemetryError as BharatiDuplicateError,
    StaleTelemetryError as BharatiStaleError,
)
from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.bharati_ml_service import BharatiMLService

CANONICAL_FIELDS = {
    "station_id",
    "sensor_id",
    "timestamp",
    "value",
    "unit",
    "quality",
    "source",
    "anomaly_score",
    "anomaly_status",
    "anomaly_type",
    "model_version",
}


@pytest.fixture
def fresh_maitri_service() -> MaitriMLService:
    service = MaitriMLService()
    service.reset_all()
    return service


@pytest.fixture
def fresh_bharati_service() -> BharatiMLService:
    service = BharatiMLService()
    service.reset_all()
    return service


class TestMLBackendInputAdaptation:
    def test_canonical_json_string_input(self):
        json_str = json.dumps({
            "station_id": "MTR",
            "sensor_id": "TEMP_001",
            "timestamp": "2026-09-17T10:30:00Z",
            "value": -15.0,
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        })
        payload = adapt_mtr_input(json_str)
        assert isinstance(payload, MaitriTelemetryInput)
        assert payload.station_id == "MTR"
        assert payload.sensor_id == "TEMP_001"
        assert payload.value == -15.0
        assert payload.quality == "GOOD"

    def test_canonical_dict_input(self):
        data = {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": "2026-09-17T10:30:00Z",
            "value": -10.5,
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        payload = adapt_brt_input(data)
        assert isinstance(payload, BharatiTelemetryInput)
        assert payload.station_id == "BRT"
        assert payload.sensor_id == "BRT_TEMP_001"
        assert payload.value == -10.5

    def test_invalid_input_payload_errors(self):
        with pytest.raises(MaitriInvalidContractError):
            adapt_mtr_input(12345)

        with pytest.raises(MaitriInvalidContractError):
            adapt_mtr_input({"station_id": "MTR", "sensor_id": "TEMP_001"})

        with pytest.raises(MaitriInvalidContractError):
            adapt_mtr_input({
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": "2026-09-17T10:30:00Z",
                "value": "not_a_valid_number",
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            })

        with pytest.raises(MaitriInvalidContractError):
            adapt_mtr_input({
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": "2026-09-17T10:30:00Z",
                "value": -15.0,
                "unit": "C",
                "quality": "INVALID_QUALITY_CODE",
                "source": "SIMULATOR",
            })


class TestMLBackendContractFlows:
    def test_insufficient_data_warmup_flow(self, fresh_maitri_service):
        base_time = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(29):
            payload = {
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": -15.0 + 0.01 * (i % 3),
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            res = process_mtr_payload(fresh_maitri_service, payload)
            assert res["anomaly_status"] == "INSUFFICIENT_DATA"
            assert res["anomaly_type"] is None
            assert res["anomaly_score"] is None
            assert res["model_version"] == "lstm-ae-v1"
            assert set(res.keys()) == CANONICAL_FIELDS

    def test_maitri_normal_inference_flow(self, fresh_maitri_service):
        base_time = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
        res = None
        for i in range(35):
            payload = {
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": -15.0 + 0.02 * (i % 4),
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            res = process_mtr_payload(fresh_maitri_service, payload)
        
        assert res is not None
        assert res["anomaly_status"] == "NORMAL"
        assert res["anomaly_type"] == "NORMAL"
        assert isinstance(res["anomaly_score"], float)
        assert res["anomaly_score"] <= fresh_maitri_service.threshold
        assert res["model_version"] == "lstm-ae-v1"

    def test_bharati_normal_inference_flow(self, fresh_bharati_service):
        base_time = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
        res = None
        for i in range(35):
            payload = {
                "station_id": "BRT",
                "sensor_id": "BRT_TEMP_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": -10.0 + 0.02 * (i % 4),
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            res = process_brt_payload(fresh_bharati_service, payload)

        assert res is not None
        assert res["anomaly_status"] == "NORMAL"
        assert res["anomaly_type"] == "NORMAL"
        assert isinstance(res["anomaly_score"], float)
        assert res["anomaly_score"] <= fresh_bharati_service.threshold
        assert res["model_version"] == "lstm-ae-bharati-v1"

    def test_spike_anomaly_flow(self, fresh_maitri_service):
        base_time = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(30):
            payload = {
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": -15.0 + 0.02 * (i % 4),
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            process_mtr_payload(fresh_maitri_service, payload)

        spike_payload = {
            "station_id": "MTR",
            "sensor_id": "TEMP_001",
            "timestamp": (base_time + timedelta(seconds=30)).isoformat(),
            "value": 45.0,  # massive sudden jump from -15 to +45
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        res = process_mtr_payload(fresh_maitri_service, spike_payload)
        assert res["anomaly_status"] == "ANOMALY"
        assert res["anomaly_type"] == "SPIKE"

    def test_drift_anomaly_flow(self, fresh_maitri_service):
        base_time = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
        drift_res = None
        for i in range(30):
            payload = {
                "station_id": "MTR",
                "sensor_id": "PRESS_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": 980.0 + 0.6 * (i + 1),
                "unit": "hPa",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            drift_res = process_mtr_payload(fresh_maitri_service, payload)

        assert drift_res is not None
        assert drift_res["anomaly_status"] == "ANOMALY"
        assert drift_res["anomaly_type"] in {"DRIFT", "UNKNOWN"}

    def test_stuck_value_and_recovery_flow(self, fresh_maitri_service):
        base_time = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
        # 1. Warm up with oscillating data
        for i in range(30):
            val = -15.0 + 0.1 * math.sin(i)
            payload = {
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": float(val),
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            process_mtr_payload(fresh_maitri_service, payload)

        # 2. Flatline constant value for 25 steps
        stuck_types_observed = []
        for i in range(30, 55):
            payload = {
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": -28.5,
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            out = process_mtr_payload(fresh_maitri_service, payload)
            if out["anomaly_status"] == "ANOMALY":
                stuck_types_observed.append(out["anomaly_type"])

        assert "STUCK_VALUE" in stuck_types_observed

        # 3. Resume oscillation
        recovered_res = None
        for i in range(55, 75):
            val = -15.0 + 0.1 * math.sin(i)
            payload = {
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": float(val),
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            recovered_res = process_mtr_payload(fresh_maitri_service, payload)

        assert recovered_res["anomaly_type"] != "STUCK_VALUE"

    def test_missing_data_and_buffer_flush(self, fresh_maitri_service):
        base_time = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
        # Warm up
        for i in range(30):
            payload = {
                "station_id": "MTR",
                "sensor_id": "HUM_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": 60.0 + 0.05 * (i % 3),
                "unit": "%",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            process_mtr_payload(fresh_maitri_service, payload)

        # Send MISSING quality point
        missing_payload = {
            "station_id": "MTR",
            "sensor_id": "HUM_001",
            "timestamp": (base_time + timedelta(seconds=30)).isoformat(),
            "value": 60.0,
            "unit": "%",
            "quality": "MISSING",
            "source": "SIMULATOR",
        }
        missing_res = process_mtr_payload(fresh_maitri_service, missing_payload)
        assert missing_res["anomaly_status"] == "MISSING_DATA"
        assert missing_res["anomaly_type"] is None
        assert missing_res["anomaly_score"] is None

        # Next valid point should encounter flushed buffer -> INSUFFICIENT_DATA
        next_payload = {
            "station_id": "MTR",
            "sensor_id": "HUM_001",
            "timestamp": (base_time + timedelta(seconds=31)).isoformat(),
            "value": 60.1,
            "unit": "%",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        next_res = process_mtr_payload(fresh_maitri_service, next_payload)
        assert next_res["anomaly_status"] == "INSUFFICIENT_DATA"

    def test_duplicate_and_stale_telemetry_errors(self, fresh_maitri_service):
        t0 = "2026-09-17T10:00:00Z"
        t1 = "2026-09-17T10:00:01Z"
        
        payload_1 = {
            "station_id": "MTR",
            "sensor_id": "VIB_001",
            "timestamp": t1,
            "value": 0.05,
            "unit": "mm/s",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        process_mtr_payload(fresh_maitri_service, payload_1)

        # Duplicate timestamp
        with pytest.raises(MaitriDuplicateError):
            process_mtr_payload(fresh_maitri_service, payload_1)

        # Stale / out of order timestamp
        stale_payload = {
            "station_id": "MTR",
            "sensor_id": "VIB_001",
            "timestamp": t0,
            "value": 0.04,
            "unit": "mm/s",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        with pytest.raises(MaitriStaleError):
            process_mtr_payload(fresh_maitri_service, stale_payload)


class TestMultiSensorIsolation:
    def test_interleaved_five_sensors_state_isolation(self, fresh_maitri_service):
        sensors = ["TEMP_001", "PRESS_001", "HUM_001", "VIB_001", "POWER_001"]
        base_vals = {
            "TEMP_001": -15.0,
            "PRESS_001": 990.0,
            "HUM_001": 55.0,
            "VIB_001": 0.85,
            "POWER_001": 35.0,
        }
        units = {
            "TEMP_001": "C",
            "PRESS_001": "hPa",
            "HUM_001": "%",
            "VIB_001": "mm/s",
            "POWER_001": "kW",
        }
        base_time = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)

        # Interleave 30 points across all 5 sensors
        for i in range(30):
            ts = (base_time + timedelta(seconds=i)).isoformat()
            for s in sensors:
                p = {
                    "station_id": "MTR",
                    "sensor_id": s,
                    "timestamp": ts,
                    "value": base_vals[s] + (i % 3) * 0.01,
                    "unit": units[s],
                    "quality": "GOOD",
                    "source": "SIMULATOR",
                }
                res = process_mtr_payload(fresh_maitri_service, p)
                if i == 29:
                    assert res["anomaly_status"] == "NORMAL"

        # Now inject a spike ONLY into TEMP_001
        ts_spike = (base_time + timedelta(seconds=30)).isoformat()
        spike_res = process_mtr_payload(fresh_maitri_service, {
            "station_id": "MTR",
            "sensor_id": "TEMP_001",
            "timestamp": ts_spike,
            "value": 50.0,
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        })
        assert spike_res["anomaly_status"] == "ANOMALY"

        # Check that PRESS_001 at the same timestamp remains unaffected and NORMAL
        press_res = process_mtr_payload(fresh_maitri_service, {
            "station_id": "MTR",
            "sensor_id": "PRESS_001",
            "timestamp": ts_spike,
            "value": base_vals["PRESS_001"] + 0.01,
            "unit": "hPa",
            "quality": "GOOD",
            "source": "SIMULATOR",
        })
        assert press_res["anomaly_status"] == "NORMAL"
        assert press_res["anomaly_type"] == "NORMAL"


class TestOutputSchemaStrictness:
    def test_json_roundtrip_and_no_nan_inf(self, fresh_maitri_service):
        base_time = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(30):
            payload = {
                "station_id": "MTR",
                "sensor_id": "POWER_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": 40.0 + (i % 2) * 0.05,
                "unit": "kW",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            res = process_mtr_payload(fresh_maitri_service, payload)

        json_serialized = json.dumps(res)
        deserialized = json.loads(json_serialized)

        assert set(deserialized.keys()) == CANONICAL_FIELDS
        for k, v in deserialized.items():
            assert v is not None
            if isinstance(v, float):
                assert str(v) not in ("nan", "inf", "-inf")
