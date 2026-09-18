"""
Backend ML Smoke Integration Regression Tests (Polarix SIH26060 - Person C).
Step 44: Verifies the in-process backend-to-ML adapter and inference boundary
across all 10 operational lifecycle scenarios.
"""

from __future__ import annotations

import json
import math
import pytest
from datetime import datetime, timedelta, timezone

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
    DuplicateTelemetryError as MTR_DuplicateError,
    InvalidContractError as MTR_InvalidContractError,
    StaleTelemetryError as MTR_StaleError,
    TelemetryInput,
    UnsupportedSensorError as MTR_UnsupportedSensorError,
    UnsupportedStationError as MTR_UnsupportedStationError,
)
from ml.inference.bharati_inference_contract import (
    BharatiTelemetryInput,
    DuplicateTelemetryError as BRT_DuplicateError,
    InvalidContractError as BRT_InvalidContractError,
    StaleTelemetryError as BRT_StaleError,
    UnsupportedSensorError as BRT_UnsupportedSensorError,
    UnsupportedStationError as BRT_UnsupportedStationError,
)
from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.bharati_ml_service import BharatiMLService

EXPECTED_OUTPUT_KEYS = {
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
def clean_maitri_service() -> MaitriMLService:
    service = MaitriMLService()
    service.reset_all()
    return service


@pytest.fixture
def clean_bharati_service() -> BharatiMLService:
    service = BharatiMLService()
    service.reset_all()
    return service


class TestBackendMLSmokeIntegration:
    def test_1_schema_ingestion_and_field_normalization(self):
        """Verify dictionary and JSON string ingestion into canonical contracts."""
        payload_dict = {
            "station_id": "MTR",
            "sensor_id": "TEMP_001",
            "timestamp": "2026-09-18T12:00:00Z",
            "value": -15.0,
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        res_d = adapt_mtr_input(payload_dict)
        res_j = adapt_mtr_input(json.dumps(payload_dict))

        assert isinstance(res_d, TelemetryInput)
        assert res_d.station_id == "MTR"
        assert res_d.value == -15.0
        assert res_j.value == -15.0

    def test_2_insufficient_data_warmup_progression(self, clean_maitri_service):
        """Verify steps 1..29 return INSUFFICIENT_DATA and null score."""
        for step in range(1, 30):
            res = process_mtr_payload(
                clean_maitri_service,
                {
                    "station_id": "MTR",
                    "sensor_id": "TEMP_001",
                    "timestamp": f"2026-09-18T00:{step:02d}:00Z",
                    "value": -15.0 + 0.01 * (step % 3),
                },
            )
            assert res["anomaly_status"] == "INSUFFICIENT_DATA"
            assert res["anomaly_score"] is None
            assert res["anomaly_type"] is None
            assert set(res.keys()) == EXPECTED_OUTPUT_KEYS

    def test_3_steady_state_normal_inference(self, clean_maitri_service, clean_bharati_service):
        """Verify 30-step nominal stationary sequence yields NORMAL status."""
        for step in range(1, 31):
            res_m = process_mtr_payload(
                clean_maitri_service,
                {
                    "station_id": "MTR",
                    "sensor_id": "TEMP_001",
                    "timestamp": f"2026-09-18T00:{step:02d}:00Z",
                    "value": -15.0 + 0.01 * (step % 3),
                },
            )
            res_b = process_brt_payload(
                clean_bharati_service,
                {
                    "station_id": "BRT",
                    "sensor_id": "BRT_TEMP_001",
                    "timestamp": f"2026-09-18T00:{step:02d}:00Z",
                    "value": -10.0 + 0.01 * (step % 3),
                },
            )

        assert res_m["anomaly_status"] == "NORMAL"
        assert res_m["anomaly_type"] == "NORMAL"
        assert res_m["anomaly_score"] <= clean_maitri_service.threshold
        assert res_m["model_version"] == "lstm-ae-v1"

        assert res_b["anomaly_status"] == "NORMAL"
        assert res_b["anomaly_type"] == "NORMAL"
        assert res_b["anomaly_score"] <= clean_bharati_service.threshold
        assert res_b["model_version"] == "lstm-ae-bharati-v1"

    def test_4_spike_anomaly_classification(self, clean_maitri_service):
        """Verify high-amplitude step jump triggers ANOMALY status and SPIKE type."""
        for step in range(1, 30):
            process_mtr_payload(
                clean_maitri_service,
                {
                    "station_id": "MTR",
                    "sensor_id": "TEMP_001",
                    "timestamp": f"2026-09-18T00:{step:02d}:00Z",
                    "value": -15.0,
                },
            )
        # 30th point is a sudden 60C shock jump
        res = process_mtr_payload(
            clean_maitri_service,
            {
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": "2026-09-18T00:30:00Z",
                "value": 45.0,
            },
        )
        assert res["anomaly_status"] == "ANOMALY"
        assert res["anomaly_type"] == "SPIKE"

    def test_5_drift_anomaly_classification(self, clean_maitri_service):
        """Verify persistent monotonic linear trend produces DRIFT/UNKNOWN anomaly."""
        res = None
        for step in range(1, 31):
            res = process_mtr_payload(
                clean_maitri_service,
                {
                    "station_id": "MTR",
                    "sensor_id": "PRESS_001",
                    "timestamp": f"2026-09-18T01:{step:02d}:00Z",
                    "value": 980.0 + 0.6 * step,
                },
            )
        assert res is not None
        assert res["anomaly_status"] == "ANOMALY"
        assert res["anomaly_type"] in {"DRIFT", "UNKNOWN"}

    def test_6_stuck_value_detection_and_recovery(self, clean_maitri_service):
        """Verify flatline produces STUCK_VALUE and subsequent oscillation clears it."""
        base_t = datetime(2026, 9, 18, 2, 0, 0, tzinfo=timezone.utc)
        # 1. Warmup
        for step in range(1, 31):
            ts = (base_t + timedelta(minutes=step)).isoformat()
            process_mtr_payload(
                clean_maitri_service,
                {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": ts, "value": -15.0 + 0.1 * math.sin(step)},
            )
        # 2. Offset flatline
        stuck_types = []
        for step in range(31, 56):
            ts = (base_t + timedelta(minutes=step)).isoformat()
            out = process_mtr_payload(
                clean_maitri_service,
                {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": ts, "value": -28.5},
            )
            if out["anomaly_status"] == "ANOMALY":
                stuck_types.append(out["anomaly_type"])

        assert "STUCK_VALUE" in stuck_types

        # 3. Recovery
        rec_res = None
        for step in range(56, 75):
            ts = (base_t + timedelta(minutes=step)).isoformat()
            rec_res = process_mtr_payload(
                clean_maitri_service,
                {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": ts, "value": -15.0 + 0.1 * math.sin(step)},
            )
        assert rec_res is not None
        assert rec_res["anomaly_type"] != "STUCK_VALUE"

    def test_7_missing_data_quality_and_buffer_flush(self, clean_maitri_service):
        """Verify MISSING quality packet triggers MISSING_DATA and flushes history."""
        for step in range(1, 31):
            process_mtr_payload(
                clean_maitri_service,
                {"station_id": "MTR", "sensor_id": "HUM_001", "timestamp": f"2026-09-18T03:{step:02d}:00Z", "value": 55.0},
            )
        drop_res = process_mtr_payload(
            clean_maitri_service,
            {"station_id": "MTR", "sensor_id": "HUM_001", "timestamp": "2026-09-18T03:31:00Z", "value": 55.0, "quality": "MISSING"},
        )
        assert drop_res["anomaly_status"] == "MISSING_DATA"
        assert drop_res["anomaly_score"] is None
        assert clean_maitri_service.get_buffer_length("HUM_001") == 0

    def test_8_multi_sensor_stream_isolation(self, clean_maitri_service):
        """Verify interleaved telemetry across 5 sensors remains completely isolated."""
        sensors = ["TEMP_001", "PRESS_001", "HUM_001", "VIB_001", "POWER_001"]
        base_vals = {"TEMP_001": -15.0, "PRESS_001": 990.0, "HUM_001": 55.0, "VIB_001": 0.85, "POWER_001": 35.0}

        for step in range(1, 31):
            ts = f"2026-09-18T04:{step:02d}:00Z"
            for s in sensors:
                p = {"station_id": "MTR", "sensor_id": s, "timestamp": ts, "value": base_vals[s] + 0.01 * (step % 3)}
                process_mtr_payload(clean_maitri_service, p)

        # Inject spike ONLY on TEMP_001
        ts_spike = "2026-09-18T04:31:00Z"
        temp_out = process_mtr_payload(
            clean_maitri_service,
            {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": ts_spike, "value": 50.0},
        )
        press_out = process_mtr_payload(
            clean_maitri_service,
            {"station_id": "MTR", "sensor_id": "PRESS_001", "timestamp": ts_spike, "value": base_vals["PRESS_001"]},
        )

        assert temp_out["anomaly_status"] == "ANOMALY"
        assert press_out["anomaly_status"] == "NORMAL"
        assert press_out["anomaly_type"] == "NORMAL"

    def test_9_error_propagation_and_rejection(self, clean_maitri_service):
        """Verify invalid station, duplicate timestamp, and stale telemetry raise typed errors."""
        # Unsupported station
        with pytest.raises(MTR_UnsupportedStationError):
            process_mtr_payload(
                clean_maitri_service,
                {"station_id": "UNKNOWN_STATION", "sensor_id": "TEMP_001", "timestamp": "2026-09-18T05:00:00Z", "value": 10.0},
            )

        # Valid point
        process_mtr_payload(
            clean_maitri_service,
            {"station_id": "MTR", "sensor_id": "VIB_001", "timestamp": "2026-09-18T05:10:00Z", "value": 0.85},
        )

        # Duplicate
        with pytest.raises(MTR_DuplicateError):
            process_mtr_payload(
                clean_maitri_service,
                {"station_id": "MTR", "sensor_id": "VIB_001", "timestamp": "2026-09-18T05:10:00Z", "value": 0.85},
            )

        # Stale
        with pytest.raises(MTR_StaleError):
            process_mtr_payload(
                clean_maitri_service,
                {"station_id": "MTR", "sensor_id": "VIB_001", "timestamp": "2026-09-18T05:09:00Z", "value": 0.85},
            )

    def test_10_output_field_preservation_and_json_strictness(self, clean_maitri_service):
        """Verify output dictionary contains exact 11 fields and valid RFC JSON serialization."""
        for step in range(1, 31):
            res = process_mtr_payload(
                clean_maitri_service,
                {"station_id": "MTR", "sensor_id": "POWER_001", "timestamp": f"2026-09-18T06:{step:02d}:00Z", "value": 35.0},
            )

        serialized = json.dumps(res)
        deserialized = json.loads(serialized)
        assert set(deserialized.keys()) == EXPECTED_OUTPUT_KEYS
        for k, v in deserialized.items():
            if isinstance(v, float):
                assert math.isfinite(v)
