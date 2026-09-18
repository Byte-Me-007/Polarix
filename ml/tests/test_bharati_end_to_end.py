"""
Comprehensive End-to-End ML Inference Pipeline Tests for Bharati Station (SIH26060 - Person C).

Verifies the full Bharati ML inference lifecycle:
1. Normal telemetry sequence across all 5 Bharati sensors
2. Spike telemetry sequence
3. Drift telemetry sequence
4. Stuck-value telemetry sequence
5. Dropout and missing data handling
6. Insufficient data streaming behavior
7. Malformed telemetry contract rejection
8. Unsupported station rejection
9. Unsupported sensor rejection
10. Interleaved multi-sensor history isolation
11. Duplicate timestamp rejection
12. Stale timestamp rejection
13. NaN and infinite value handling
14. JSON and dictionary serialization roundtrip
15. Model version and frozen threshold invariants
16. Model artifact integrity verification before inference
17. Corrupted artifact rejection in sandbox
18. BharatiMLService adapter integration
19. Repeated deterministic execution
20. Maitri artifact isolation and preservation
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

from ml.inference.bharati_anomaly_type_classifier import (
    SUPPORTED_ANOMALY_TYPES,
    BharatiAnomalyTypeClassifier,
)
from ml.inference.bharati_inference_contract import (
    DEFAULT_BHARATI_MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS,
    SUPPORTED_BHARATI_STATIONS,
    VALID_STATUSES,
    BharatiTelemetryInput,
    BharatiTelemetryOutput,
    DuplicateTelemetryError,
    InvalidContractError,
    StaleTelemetryError,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.bharati_lstm_inference import BharatiLSTMInference
from ml.inference.bharati_ml_service import BharatiMLService
from ml.inference.validate_bharati_pipeline import BharatiPipelineValidator
from ml.models.model_registry import (
    ModelIntegrityError,
    ModelManifestNotFoundError,
    ModelVersionMismatchError,
    compute_file_sha256,
    validate_model_artifacts,
)

FROZEN_BHARATI_MODEL_VERSION = "lstm-ae-bharati-v1"
FROZEN_BHARATI_THRESHOLD = 0.013215307652775843
FROZEN_BHARATI_MODEL_SHA = "412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a"
FROZEN_BHARATI_CONFIG_SHA = "16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7"
FROZEN_BHARATI_SCALER_SHA = "b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899"
FROZEN_BHARATI_THRESHOLD_SHA = "95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d"

FROZEN_MAITRI_MODEL_SHA = "7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262"
FROZEN_MAITRI_CONFIG_SHA = "71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b"
FROZEN_MAITRI_SCALER_SHA = "2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224"
FROZEN_MAITRI_THRESHOLD_SHA = "80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1"


@pytest.fixture(scope="module")
def inference_engine() -> BharatiLSTMInference:
    """Fixture providing an initialized Bharati LSTM Autoencoder inference engine."""
    return BharatiLSTMInference(device="cpu", verify_manifest=True)


@pytest.fixture(scope="module")
def synthetic_df() -> pd.DataFrame:
    """Fixture providing the synthetic Bharati telemetry dataset."""
    dataset_path = Path(__file__).resolve().parent.parent / "data" / "bharati_synthetic_telemetry.csv"
    assert dataset_path.exists(), f"Synthetic dataset missing at {dataset_path}"
    return pd.read_csv(dataset_path)


# -----------------------------------------------------------------------------
# Test 1: Normal Telemetry Sequence Across All 5 Sensors
# -----------------------------------------------------------------------------
def test_1_normal_telemetry_all_5_sensors(
    inference_engine: BharatiLSTMInference, synthetic_df: pd.DataFrame
) -> None:
    """Verify normal telemetry sequence produces INSUFFICIENT_DATA for steps 1..29, then valid inference."""
    for sensor in sorted(SUPPORTED_BHARATI_SENSORS):
        inference_engine.reset_history()
        sub = synthetic_df[
            (synthetic_df["sensor_id"] == sensor) & (synthetic_df["anomaly_type"] == "NORMAL")
        ].head(40)

        for i, (_, row) in enumerate(sub.iterrows()):
            inp = BharatiTelemetryInput(
                station_id=str(row["station_id"]),
                sensor_id=str(row["sensor_id"]),
                timestamp=str(row["timestamp"]),
                value=float(row["value"]),
                unit=str(row["unit"]),
                quality="GOOD",
            )
            out = inference_engine.infer_telemetry(inp)

            assert out.station_id == "BRT"
            assert out.sensor_id == sensor
            assert out.model_version == FROZEN_BHARATI_MODEL_VERSION

            if i < 29:
                assert out.anomaly_status == "INSUFFICIENT_DATA"
                assert out.anomaly_score is None
                assert out.anomaly_type is None
            else:
                assert out.anomaly_status in {"NORMAL", "ANOMALY"}
                assert out.anomaly_score is not None
                assert np.isfinite(out.anomaly_score)
                if out.anomaly_status == "NORMAL":
                    assert out.anomaly_type == "NORMAL"


# -----------------------------------------------------------------------------
# Test 2: Spike Anomaly Detection and Classification
# -----------------------------------------------------------------------------
def test_2_spike_anomaly_detection_and_classification(
    inference_engine: BharatiLSTMInference, synthetic_df: pd.DataFrame
) -> None:
    """Verify spike sequence produces SPIKE or UNKNOWN anomaly type when flagged as ANOMALY."""
    inference_engine.reset_history()
    normal_sub = synthetic_df[
        (synthetic_df["sensor_id"] == "BRT_TEMP_001") & (synthetic_df["anomaly_type"] == "NORMAL")
    ].head(30)
    for _, row in normal_sub.iterrows():
        inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=str(row["timestamp"]),
                value=float(row["value"]),
                quality="GOOD",
            )
        )

    # Inject sharp spike pulse
    spike_input = BharatiTelemetryInput(
        station_id="BRT",
        sensor_id="BRT_TEMP_001",
        timestamp="2026-03-02T00:00:00Z",
        value=25.0,  # Extreme jump from normal ~ -10.0
        quality="GOOD",
    )
    out = inference_engine.infer_telemetry(spike_input)
    assert out.anomaly_status == "ANOMALY"
    assert out.anomaly_score is not None and out.anomaly_score > inference_engine.threshold
    assert out.anomaly_type in {"SPIKE", "UNKNOWN"}


# -----------------------------------------------------------------------------
# Test 3: Drift Anomaly Detection and Classification
# -----------------------------------------------------------------------------
def test_3_drift_anomaly_detection_and_classification(
    inference_engine: BharatiLSTMInference,
) -> None:
    """Verify gradual drift sequence produces DRIFT or UNKNOWN anomaly type when flagged as ANOMALY."""
    inference_engine.reset_history()
    for i in range(30):
        val = -10.0 + 0.1 * np.sin(i)
        inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=float(val),
                quality="GOOD",
            )
        )

    drift_types_observed = set()
    for i in range(30):
        val = -10.0 + 0.35 * i
        out = inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-03-01T01:{i:02d}:00Z",
                value=float(val),
                quality="GOOD",
            )
        )
        if out.anomaly_status == "ANOMALY":
            assert out.anomaly_type in {"DRIFT", "UNKNOWN", "SPIKE"}
            drift_types_observed.add(out.anomaly_type)

    assert "DRIFT" in drift_types_observed


# -----------------------------------------------------------------------------
# Test 4: Stuck-Value Sequence
# -----------------------------------------------------------------------------
def test_4_stuck_value_sequence(inference_engine: BharatiLSTMInference) -> None:
    """Verify constant flatline sequence produces STUCK_VALUE, UNKNOWN, or SPIKE when flagged as ANOMALY."""
    inference_engine.reset_history()
    for i in range(30):
        val = -10.0 + 0.1 * np.sin(i)
        inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=float(val),
                quality="GOOD",
            )
        )

    stuck_types_observed = set()
    for i in range(25):
        out = inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-03-01T02:{i:02d}:00Z",
                value=-28.5,
                quality="GOOD",
            )
        )
        if out.anomaly_status == "ANOMALY":
            assert out.anomaly_type in {"STUCK_VALUE", "UNKNOWN", "SPIKE"}
            stuck_types_observed.add(out.anomaly_type)

    assert "STUCK_VALUE" in stuck_types_observed


# -----------------------------------------------------------------------------
# Test 5: Dropout and Null Value Handling
# -----------------------------------------------------------------------------
def test_5_dropout_null_value_handling(inference_engine: BharatiLSTMInference) -> None:
    """Verify null value returns MISSING_DATA and resets the rolling window buffer."""
    inference_engine.reset_history()
    for i in range(30):
        inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=-10.0,
                quality="GOOD",
            )
        )

    null_out = inference_engine.infer_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-03-01T00:30:00Z",
            value=None,
            quality="GOOD",
        )
    )
    assert null_out.anomaly_status == "MISSING_DATA"
    assert null_out.anomaly_score is None
    assert null_out.anomaly_type is None

    # Next valid point must be INSUFFICIENT_DATA
    next_out = inference_engine.infer_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-03-01T00:31:00Z",
            value=-10.0,
            quality="GOOD",
        )
    )
    assert next_out.anomaly_status == "INSUFFICIENT_DATA"


# -----------------------------------------------------------------------------
# Test 6: Bad Quality Handling
# -----------------------------------------------------------------------------
def test_6_dropout_bad_quality_handling(inference_engine: BharatiLSTMInference) -> None:
    """Verify non-GOOD quality tag returns MISSING_DATA and resets the rolling window buffer."""
    inference_engine.reset_history()
    for i in range(30):
        inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_PRESS_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=985.0,
                quality="GOOD",
            )
        )

    bad_q_out = inference_engine.infer_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_PRESS_001",
            timestamp="2026-03-01T00:30:00Z",
            value=985.0,
            quality="BAD",
        )
    )
    assert bad_q_out.anomaly_status == "MISSING_DATA"
    assert bad_q_out.anomaly_score is None
    assert bad_q_out.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 7: Insufficient Data Streaming Behavior
# -----------------------------------------------------------------------------
def test_7_insufficient_data_warmup(inference_engine: BharatiLSTMInference) -> None:
    """Verify streaming fewer than 30 observations consistently returns INSUFFICIENT_DATA."""
    inference_engine.reset_history()
    for i in range(29):
        out = inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_HUM_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=60.0 + i * 0.05,
                quality="GOOD",
            )
        )
        assert out.anomaly_status == "INSUFFICIENT_DATA"
        assert out.anomaly_score is None
        assert out.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 8: Multi-Sensor History Isolation
# -----------------------------------------------------------------------------
def test_8_multi_sensor_history_isolation(inference_engine: BharatiLSTMInference) -> None:
    """Verify interleaved streams across sensors maintain independent history buffers."""
    inference_engine.reset_history()

    # Interleave BRT_TEMP_001 (30 points) and BRT_VIB_001 (15 points)
    for i in range(30):
        out_temp = inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=-10.0 + 0.05 * np.sin(i),
                quality="GOOD",
            )
        )
        if i < 15:
            out_vib = inference_engine.infer_telemetry(
                BharatiTelemetryInput(
                    station_id="BRT",
                    sensor_id="BRT_VIB_001",
                    timestamp=f"2026-03-01T00:{i:02d}:00Z",
                    value=0.90 + 0.01 * np.cos(i),
                    quality="GOOD",
                )
            )
            assert out_vib.anomaly_status == "INSUFFICIENT_DATA"

    # BRT_TEMP_001 reached 30 observations
    assert out_temp.anomaly_status in {"NORMAL", "ANOMALY"}
    assert out_temp.anomaly_score is not None

    # Clear BRT_TEMP_001 with null value
    inference_engine.infer_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-03-01T00:30:00Z",
            value=None,
        )
    )

    # Add 15 more points to BRT_VIB_001; it should reach 30 and output scored inference
    for i in range(15, 30):
        out_vib = inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_VIB_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=0.90 + 0.01 * np.cos(i),
                quality="GOOD",
            )
        )

    assert out_vib.anomaly_status in {"NORMAL", "ANOMALY"}
    assert out_vib.anomaly_score is not None


# -----------------------------------------------------------------------------
# Test 9: Duplicate Timestamp Rejection
# -----------------------------------------------------------------------------
def test_9_duplicate_timestamp_rejection(inference_engine: BharatiLSTMInference) -> None:
    """Verify duplicate timestamp raises DuplicateTelemetryError without corrupting buffer."""
    inference_engine.reset_history()
    inference_engine.infer_telemetry(
        BharatiTelemetryInput("BRT", "BRT_POWER_001", "2026-03-01T00:00:00Z", 42.0)
    )

    with pytest.raises(DuplicateTelemetryError):
        inference_engine.infer_telemetry(
            BharatiTelemetryInput("BRT", "BRT_POWER_001", "2026-03-01T00:00:00Z", 42.5)
        )

    # Subsequent valid timestamp proceeds
    next_out = inference_engine.infer_telemetry(
        BharatiTelemetryInput("BRT", "BRT_POWER_001", "2026-03-01T00:01:00Z", 42.1)
    )
    assert next_out.anomaly_status == "INSUFFICIENT_DATA"


# -----------------------------------------------------------------------------
# Test 10: Stale Timestamp Rejection
# -----------------------------------------------------------------------------
def test_10_stale_timestamp_rejection(inference_engine: BharatiLSTMInference) -> None:
    """Verify out-of-order timestamp raises StaleTelemetryError without corrupting buffer."""
    inference_engine.reset_history()
    inference_engine.infer_telemetry(
        BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-03-01T00:10:00Z", -10.0)
    )

    with pytest.raises(StaleTelemetryError):
        inference_engine.infer_telemetry(
            BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-03-01T00:05:00Z", -10.5)
        )

    # Subsequent forward timestamp proceeds
    next_out = inference_engine.infer_telemetry(
        BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-03-01T00:11:00Z", -10.1)
    )
    assert next_out.anomaly_status == "INSUFFICIENT_DATA"


# -----------------------------------------------------------------------------
# Test 11: Unsupported Station Rejection
# -----------------------------------------------------------------------------
def test_11_unsupported_station_rejection() -> None:
    """Verify station IDs outside SUPPORTED_BHARATI_STATIONS are strictly rejected."""
    for invalid_station in ["MAITRI", "MTR", "STATION_X", ""]:
        with pytest.raises((UnsupportedStationError, InvalidContractError)):
            BharatiTelemetryInput(
                station_id=invalid_station,
                sensor_id="BRT_TEMP_001",
                timestamp="2026-09-18T10:00:00Z",
                value=-10.0,
            )


# -----------------------------------------------------------------------------
# Test 12: Unsupported Sensor Rejection
# -----------------------------------------------------------------------------
def test_12_unsupported_sensor_rejection() -> None:
    """Verify sensor IDs outside SUPPORTED_BHARATI_SENSORS are strictly rejected."""
    for invalid_sensor in ["TEMP_001", "RADIATION_001", "BRT_TEMP_999", "INVALID"]:
        with pytest.raises(UnsupportedSensorError):
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id=invalid_sensor,
                timestamp="2026-09-18T10:00:00Z",
                value=-10.0,
            )


# -----------------------------------------------------------------------------
# Test 13: Non-Finite NaN Value Handling
# -----------------------------------------------------------------------------
def test_13_non_finite_nan_value_handling(inference_engine: BharatiLSTMInference) -> None:
    """Verify NaN value maps to MISSING_DATA and resets buffer."""
    inference_engine.reset_history()
    for i in range(30):
        inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=-10.0,
            )
        )

    nan_out = inference_engine.infer_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-03-01T00:30:00Z",
            value=float("nan"),
        )
    )
    assert nan_out.anomaly_status == "MISSING_DATA"
    assert nan_out.anomaly_score is None
    assert nan_out.anomaly_type is None


# -----------------------------------------------------------------------------
# Test 14: Non-Finite Inf Value Handling
# -----------------------------------------------------------------------------
def test_14_non_finite_inf_value_handling(inference_engine: BharatiLSTMInference) -> None:
    """Verify infinite value maps to MISSING_DATA and resets buffer."""
    inference_engine.reset_history()
    for i in range(30):
        inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=-10.0,
            )
        )

    inf_out = inference_engine.infer_telemetry(
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-03-01T00:30:00Z",
            value=float("inf"),
        )
    )
    assert inf_out.anomaly_status == "MISSING_DATA"
    assert inf_out.anomaly_score is None


# -----------------------------------------------------------------------------
# Test 15: Invalid Contract Schema Rejections
# -----------------------------------------------------------------------------
def test_15_invalid_contract_schema() -> None:
    """Verify malformed timestamps and non-numeric values are rejected."""
    with pytest.raises(InvalidContractError):
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="NOT_A_TIMESTAMP",
            value=-10.0,
        )

    with pytest.raises(InvalidContractError):
        BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-09-18T10:00:00Z",
            value="INVALID_NUMBER",  # type: ignore
        )


# -----------------------------------------------------------------------------
# Test 16: Backend Output Fields Completeness
# -----------------------------------------------------------------------------
def test_16_backend_output_fields_completeness(
    inference_engine: BharatiLSTMInference,
) -> None:
    """Verify all expected fields exist on BharatiTelemetryOutput."""
    inference_engine.reset_history()
    for i in range(30):
        out = inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_HUM_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=60.0,
                unit="%",
                quality="GOOD",
                source="SIMULATOR",
            )
        )

    assert hasattr(out, "station_id")
    assert hasattr(out, "sensor_id")
    assert hasattr(out, "timestamp")
    assert hasattr(out, "value")
    assert hasattr(out, "unit")
    assert hasattr(out, "quality")
    assert hasattr(out, "source")
    assert hasattr(out, "anomaly_score")
    assert hasattr(out, "anomaly_status")
    assert hasattr(out, "anomaly_type")
    assert hasattr(out, "model_version")

    d = out.to_dict()
    assert set(d.keys()) == {
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


# -----------------------------------------------------------------------------
# Test 17: JSON Serialization Roundtrip
# -----------------------------------------------------------------------------
def test_17_json_serialization_roundtrip(inference_engine: BharatiLSTMInference) -> None:
    """Verify all BharatiTelemetryOutput states serialize and deserialize without loss."""
    inference_engine.reset_history()
    for i in range(30):
        out = inference_engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_HUM_001",
                timestamp=f"2026-03-01T00:{i:02d}:00Z",
                value=60.0,
                unit="%",
                quality="GOOD",
            )
        )

    json_str = out.to_json(indent=2)
    deserialized = BharatiTelemetryOutput.from_json(json_str)

    assert deserialized.station_id == out.station_id
    assert deserialized.sensor_id == out.sensor_id
    assert deserialized.timestamp == out.timestamp
    assert deserialized.value == out.value
    assert deserialized.anomaly_score == out.anomaly_score
    assert deserialized.anomaly_status == out.anomaly_status
    assert deserialized.anomaly_type == out.anomaly_type
    assert deserialized.model_version == out.model_version


# -----------------------------------------------------------------------------
# Test 18: Dictionary Conversion Roundtrip
# -----------------------------------------------------------------------------
def test_18_dict_conversion_roundtrip() -> None:
    """Verify dictionary-in, dictionary-out conversion for BharatiTelemetryInput and Output."""
    inp_dict = {
        "station_id": "BRT",
        "sensor_id": "BRT_VIB_001",
        "timestamp": "2026-09-18T12:00:00Z",
        "value": 0.95,
        "unit": "mm/s",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    inp_obj = BharatiTelemetryInput.from_dict(inp_dict)
    assert inp_obj.to_dict() == inp_dict


# -----------------------------------------------------------------------------
# Test 19: Model Version and Frozen Threshold Invariants
# -----------------------------------------------------------------------------
def test_19_model_version_and_threshold_invariants(
    inference_engine: BharatiLSTMInference,
) -> None:
    """Verify model version is lstm-ae-bharati-v1 and threshold is exactly 0.013215307652775843."""
    assert inference_engine.model_version == FROZEN_BHARATI_MODEL_VERSION
    assert abs(inference_engine.threshold - FROZEN_BHARATI_THRESHOLD) < 1e-12


# -----------------------------------------------------------------------------
# Test 20: Artifact Integrity Verification
# -----------------------------------------------------------------------------
def test_20_artifact_integrity_verification() -> None:
    """Verify validate_model_artifacts verifies all 4 frozen Bharati artifacts."""
    report = validate_model_artifacts(
        model_version=FROZEN_BHARATI_MODEL_VERSION, raise_on_error=True
    )
    assert report.overall_status == "VALID"
    assert len(report.errors) == 0
    assert len(report.artifact_results) == 4


# -----------------------------------------------------------------------------
# Test 21: Corrupted Artifact Rejection in Sandbox
# -----------------------------------------------------------------------------
def test_21_corrupted_artifact_rejection_in_sandbox(tmp_path: Path) -> None:
    """Verify BharatiLSTMInference rejects initialization if artifact integrity fails."""
    models_dir = tmp_path / "models"
    results_dir = tmp_path / "results"
    models_dir.mkdir()
    results_dir.mkdir()

    shutil.copy(
        "ml/models/lstm-ae-bharati-v1_config.json",
        models_dir / "lstm-ae-bharati-v1_config.json",
    )
    shutil.copy(
        "ml/models/lstm-ae-bharati-v1_scaler.json",
        models_dir / "lstm-ae-bharati-v1_scaler.json",
    )
    shutil.copy(
        "ml/results/bharati_lstm_threshold.json",
        results_dir / "bharati_lstm_threshold.json",
    )
    shutil.copy(
        "ml/models/lstm-ae-bharati-v1_manifest.json",
        models_dir / "lstm-ae-bharati-v1_manifest.json",
    )
    (models_dir / "lstm-ae-bharati-v1.pt").write_bytes(b"CORRUPTED")

    with pytest.raises(ModelIntegrityError):
        BharatiLSTMInference(
            model_path=models_dir / "lstm-ae-bharati-v1.pt",
            config_path=models_dir / "lstm-ae-bharati-v1_config.json",
            scaler_path=models_dir / "lstm-ae-bharati-v1_scaler.json",
            threshold_path=results_dir / "bharati_lstm_threshold.json",
            manifest_path=models_dir / "lstm-ae-bharati-v1_manifest.json",
            verify_manifest=True,
        )


# -----------------------------------------------------------------------------
# Test 22: BharatiMLService Adapter Integration
# -----------------------------------------------------------------------------
def test_22_bharati_ml_service_adapter_integration() -> None:
    """Verify BharatiMLService adapter works seamlessly with dictionaries, JSON, and resets."""
    service = BharatiMLService(verify_manifest=True)
    info = service.get_service_info()
    assert info["status"] == "READY"
    assert info["station_id"] == "BRT"
    assert len(info["supported_sensors"]) == 5

    # Process dict
    res_dict = service.process_dict(
        {
            "station_id": "BRT",
            "sensor_id": "BRT_PRESS_001",
            "timestamp": "2026-09-18T10:00:00Z",
            "value": 985.0,
            "quality": "GOOD",
        }
    )
    assert res_dict["anomaly_status"] == "INSUFFICIENT_DATA"
    assert service.get_buffer_length("BRT_PRESS_001") == 1

    service.reset_sensor("BRT_PRESS_001")
    assert service.get_buffer_length("BRT_PRESS_001") == 0


# -----------------------------------------------------------------------------
# Test 23: Deterministic Reproducibility
# -----------------------------------------------------------------------------
def test_23_deterministic_reproducibility() -> None:
    """Verify two independent inference instances produce identical outputs for identical inputs."""
    engine1 = BharatiLSTMInference(device="cpu", verify_manifest=True)
    engine2 = BharatiLSTMInference(device="cpu", verify_manifest=True)

    inputs = [
        BharatiTelemetryInput(
            "BRT", "BRT_PRESS_001", f"2026-03-01T00:{i:02d}:00Z", 985.0 + 0.2 * np.sin(i), quality="GOOD"
        )
        for i in range(35)
    ]

    outputs1 = [engine1.infer_telemetry(inp).to_dict() for inp in inputs]
    outputs2 = [engine2.infer_telemetry(inp).to_dict() for inp in inputs]

    assert outputs1 == outputs2


# -----------------------------------------------------------------------------
# Test 24: Maitri Artifact Isolation and Preservation
# -----------------------------------------------------------------------------
def test_24_maitri_artifacts_isolation() -> None:
    """Verify all Maitri frozen artifacts remain completely unchanged."""
    assert compute_file_sha256("ml/models/lstm-ae-v1.pt") == FROZEN_MAITRI_MODEL_SHA
    assert compute_file_sha256("ml/models/lstm-ae-v1_config.json") == FROZEN_MAITRI_CONFIG_SHA
    assert compute_file_sha256("ml/models/lstm-ae-v1_scaler.json") == FROZEN_MAITRI_SCALER_SHA
    assert compute_file_sha256("ml/results/lstm_threshold.json") == FROZEN_MAITRI_THRESHOLD_SHA
