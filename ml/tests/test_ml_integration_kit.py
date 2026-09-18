"""
Integration Kit Test Suite for Person A Backend Interface.
Step 45: Validates all documented APIs, lifecycle patterns, and contract guarantees
presented in ml/INTEGRATION_KIT.md and ml/results/ml_integration_kit_contract.json.
"""

from __future__ import annotations

import json
import math
import pytest
from datetime import datetime, timedelta, timezone

from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.bharati_ml_service import BharatiMLService
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
    DEFAULT_MODEL_VERSION as MAITRI_MODEL_VERSION,
    SUPPORTED_SENSORS as MAITRI_SENSORS,
    SUPPORTED_STATIONS as MAITRI_STATIONS,
    VALID_QUALITIES,
    DuplicateTelemetryError as MaitriDuplicateError,
    InvalidContractError as MaitriInvalidContractError,
    StaleTelemetryError as MaitriStaleError,
    UnsupportedSensorError as MaitriUnsupportedSensorError,
    UnsupportedStationError as MaitriUnsupportedStationError,
)
from ml.inference.bharati_inference_contract import (
    DEFAULT_BHARATI_MODEL_VERSION as BHARATI_MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS as BHARATI_SENSORS,
    SUPPORTED_BHARATI_STATIONS as BHARATI_STATIONS,
    DuplicateTelemetryError as BharatiDuplicateError,
    InvalidContractError as BharatiInvalidContractError,
    StaleTelemetryError as BharatiStaleError,
    UnsupportedSensorError as BharatiUnsupportedSensorError,
    UnsupportedStationError as BharatiUnsupportedStationError,
)
from ml.inference.anomaly_type_classifier import SUPPORTED_ANOMALY_TYPES

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

VALID_STATUS_VOCABULARY = {"NORMAL", "ANOMALY", "INSUFFICIENT_DATA", "MISSING_DATA"}


@pytest.fixture
def fresh_mtr_service() -> MaitriMLService:
    service = MaitriMLService()
    service.reset_all()
    return service


@pytest.fixture
def fresh_brt_service() -> BharatiMLService:
    service = BharatiMLService()
    service.reset_all()
    return service


class TestIntegrationKitGuarantees:
    def test_1_documented_imports_exist(self):
        """1. Verify that all documented imports in Section 2 exist and are callable."""
        assert callable(MaitriMLService)
        assert callable(BharatiMLService)
        assert callable(adapt_mtr_input)
        assert callable(adapt_mtr_output)
        assert callable(process_mtr_payload)
        assert callable(adapt_brt_input)
        assert callable(adapt_brt_output)
        assert callable(process_brt_payload)

    def test_2_service_lifecycle_singleton_state_accumulation(self, fresh_mtr_service):
        """2. Verify that singleton service retains sequence state across sequential invocations."""
        base_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
        assert fresh_mtr_service.get_buffer_length("TEMP_001") == 0

        for i in range(1, 11):
            ts = (base_time + timedelta(seconds=i)).isoformat()
            process_mtr_payload(
                fresh_mtr_service,
                {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": ts, "value": -15.0},
            )
            assert fresh_mtr_service.get_buffer_length("TEMP_001") == i

    def test_3_maitri_example_execution(self, fresh_mtr_service):
        """3. Verify Section 5 Maitri integration example executes and produces valid output."""
        base_time = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)
        res = None
        for step in range(1, 31):
            packet = {
                "station_id": "MTR",
                "sensor_id": "TEMP_001",
                "timestamp": (base_time + timedelta(seconds=step)).isoformat(),
                "value": -15.0 + 0.01 * (step % 3),
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            res = process_mtr_payload(fresh_mtr_service, packet)

        assert res is not None
        assert res["station_id"] == "MTR"
        assert res["sensor_id"] == "TEMP_001"
        assert res["anomaly_status"] == "NORMAL"
        assert res["anomaly_type"] == "NORMAL"
        assert res["anomaly_score"] <= fresh_mtr_service.threshold
        assert res["model_version"] == "lstm-ae-v1"

    def test_4_bharati_example_execution(self, fresh_brt_service):
        """4. Verify Section 6 Bharati integration example executes and produces valid output."""
        base_time = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)
        res = None
        for step in range(1, 31):
            packet = {
                "station_id": "BRT",
                "sensor_id": "BRT_TEMP_001",
                "timestamp": (base_time + timedelta(seconds=step)).isoformat(),
                "value": -10.0 + 0.01 * (step % 3),
                "unit": "C",
                "quality": "GOOD",
                "source": "SIMULATOR",
            }
            res = process_brt_payload(fresh_brt_service, packet)

        assert res is not None
        assert res["station_id"] == "BRT"
        assert res["sensor_id"] == "BRT_TEMP_001"
        assert res["anomaly_status"] == "NORMAL"
        assert res["anomaly_type"] == "NORMAL"
        assert res["anomaly_score"] <= fresh_brt_service.threshold
        assert res["model_version"] == "lstm-ae-bharati-v1"

    def test_5_canonical_output_schema_and_rfc_finite_floats(self, fresh_mtr_service):
        """5. Verify canonical output has all 11 fields and strictly finite floating-point values."""
        base_time = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)
        for step in range(1, 31):
            res = process_mtr_payload(
                fresh_mtr_service,
                {
                    "station_id": "MTR",
                    "sensor_id": "PRESS_001",
                    "timestamp": (base_time + timedelta(seconds=step)).isoformat(),
                    "value": 990.0,
                    "unit": "hPa",
                    "quality": "GOOD",
                    "source": "SIMULATOR",
                },
            )

        assert set(res.keys()) == CANONICAL_FIELDS
        for k, v in res.items():
            if isinstance(v, float):
                assert math.isfinite(v)
                assert str(v) not in {"nan", "inf", "-inf"}

    def test_6_status_vocabulary_integrity(self, fresh_mtr_service):
        """6. Verify status vocabulary conforms to ['NORMAL', 'ANOMALY', 'INSUFFICIENT_DATA', 'MISSING_DATA']."""
        base_time = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)
        # 1. Warmup -> INSUFFICIENT_DATA
        out_warmup = process_mtr_payload(
            fresh_mtr_service,
            {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": (base_time + timedelta(seconds=1)).isoformat(), "value": -15.0},
        )
        assert out_warmup["anomaly_status"] in VALID_STATUS_VOCABULARY
        assert out_warmup["anomaly_status"] == "INSUFFICIENT_DATA"

        # Complete to 30 -> NORMAL
        for i in range(2, 31):
            out_norm = process_mtr_payload(
                fresh_mtr_service,
                {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": (base_time + timedelta(seconds=i)).isoformat(), "value": -15.0},
            )
        assert out_norm["anomaly_status"] in VALID_STATUS_VOCABULARY
        assert out_norm["anomaly_status"] == "NORMAL"

        # Spike -> ANOMALY
        out_anom = process_mtr_payload(
            fresh_mtr_service,
            {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": (base_time + timedelta(seconds=31)).isoformat(), "value": 45.0},
        )
        assert out_anom["anomaly_status"] in VALID_STATUS_VOCABULARY
        assert out_anom["anomaly_status"] == "ANOMALY"

        # Missing -> MISSING_DATA
        out_miss = process_mtr_payload(
            fresh_mtr_service,
            {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": (base_time + timedelta(seconds=32)).isoformat(), "value": None, "quality": "MISSING"},
        )
        assert out_miss["anomaly_status"] in VALID_STATUS_VOCABULARY
        assert out_miss["anomaly_status"] == "MISSING_DATA"

    def test_7_anomaly_type_vocabulary_integrity(self):
        """7. Verify anomaly types match {'NORMAL', 'SPIKE', 'DRIFT', 'STUCK_VALUE', 'UNKNOWN'}."""
        expected_types = {"NORMAL", "SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN"}
        assert SUPPORTED_ANOMALY_TYPES == expected_types

    def test_8_missing_data_buffer_flush_and_recovery(self, fresh_mtr_service):
        """8. Verify MISSING_DATA clears rolling history buffer and recovers cleanly upon new data."""
        base_time = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)
        # Warmup to 30
        for i in range(1, 31):
            process_mtr_payload(
                fresh_mtr_service,
                {"station_id": "MTR", "sensor_id": "HUM_001", "timestamp": (base_time + timedelta(seconds=i)).isoformat(), "value": 55.0},
            )
        assert fresh_mtr_service.get_buffer_length("HUM_001") == 30

        # Send MISSING quality
        process_mtr_payload(
            fresh_mtr_service,
            {"station_id": "MTR", "sensor_id": "HUM_001", "timestamp": (base_time + timedelta(seconds=31)).isoformat(), "value": 55.0, "quality": "MISSING"},
        )
        assert fresh_mtr_service.get_buffer_length("HUM_001") == 0

        # Resumed point is INSUFFICIENT_DATA (step 1 of new window)
        res_next = process_mtr_payload(
            fresh_mtr_service,
            {"station_id": "MTR", "sensor_id": "HUM_001", "timestamp": (base_time + timedelta(seconds=32)).isoformat(), "value": 55.0, "quality": "GOOD"},
        )
        assert res_next["anomaly_status"] == "INSUFFICIENT_DATA"
        assert fresh_mtr_service.get_buffer_length("HUM_001") == 1

    def test_9_station_and_model_isolation(self, fresh_mtr_service, fresh_brt_service):
        """9. Verify Maitri and Bharati services maintain separate configurations and states."""
        assert fresh_mtr_service.model_version == "lstm-ae-v1"
        assert fresh_brt_service.model_version == "lstm-ae-bharati-v1"
        assert fresh_mtr_service.threshold != fresh_brt_service.threshold

        # Ingesting into Maitri does not affect Bharati buffer
        process_mtr_payload(
            fresh_mtr_service,
            {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": "2026-09-18T10:00:00Z", "value": -15.0},
        )
        assert fresh_mtr_service.get_buffer_length("TEMP_001") == 1
        assert fresh_brt_service.get_buffer_length("BRT_TEMP_001") == 0

    def test_10_duplicate_and_stale_error_handling(self, fresh_mtr_service):
        """10. Verify DuplicateTelemetryError and StaleTelemetryError are raised as documented."""
        t1 = "2026-09-18T10:00:10Z"
        t0 = "2026-09-18T10:00:09Z"

        process_mtr_payload(
            fresh_mtr_service,
            {"station_id": "MTR", "sensor_id": "VIB_001", "timestamp": t1, "value": 0.85},
        )

        with pytest.raises(MaitriDuplicateError):
            process_mtr_payload(
                fresh_mtr_service,
                {"station_id": "MTR", "sensor_id": "VIB_001", "timestamp": t1, "value": 0.85},
            )

        with pytest.raises(MaitriStaleError):
            process_mtr_payload(
                fresh_mtr_service,
                {"station_id": "MTR", "sensor_id": "VIB_001", "timestamp": t0, "value": 0.85},
            )

    def test_11_deterministic_repeatability(self):
        """11. Verify two identical fresh services produce bit-exact identical predictions."""
        s1 = MaitriMLService()
        s2 = MaitriMLService()
        s1.reset_all()
        s2.reset_all()

        base_time = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(1, 35):
            packet = {
                "station_id": "MTR",
                "sensor_id": "POWER_001",
                "timestamp": (base_time + timedelta(seconds=i)).isoformat(),
                "value": 35.0 + 0.1 * (i % 4),
            }
            r1 = process_mtr_payload(s1, packet)
            r2 = process_mtr_payload(s2, packet)
            assert r1 == r2
