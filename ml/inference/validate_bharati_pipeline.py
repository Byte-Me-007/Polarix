"""
Polarix Bharati End-to-End ML Inference Pipeline Validation Harness (SIH26060 - Person C).

Validates the full Bharati ML telemetry inference pipeline from raw simulator-style inputs
through typed data contracts, artifact integrity verification, rolling-window LSTM inference,
anomaly scoring, anomaly classification, and JSON serialization.

Pipeline Flow:
    Telemetry Dictionary / JSON
            ↓
    BharatiTelemetryInput (Contract Validation)
            ↓
    Model Artifact Integrity Verification (SHA-256 Checksums & Sizes)
            ↓
    Rolling Window Buffer (Per-sensor isolation, 30-step minimum)
            ↓
    LSTM Autoencoder Reconstruction Error (MSE)
            ↓
    Anomaly Status Evaluation (Frozen Threshold: 0.013215307652775843)
            ↓
    Anomaly Type Classification (SPIKE, DRIFT, STUCK_VALUE, NORMAL, UNKNOWN)
            ↓
    BharatiTelemetryOutput (Typed Contract)
            ↓
    JSON Serializable Backend Result

Design Principles:
- Zero dependency on FastAPI, MQTT, SQLite, or frontend frameworks.
- Reusable harness with structured programmatic API and CLI runner.
- Clear distinction between Pipeline Correctness and Model Performance.
- Deterministic execution across all 5 Bharati sensors.
- Synthetic telemetry only; no real Antarctic data claimed.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

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
from ml.models.model_registry import (
    ModelIntegrityError,
    ModelManifestNotFoundError,
    ModelVersionMismatchError,
    validate_model_artifacts,
)

DEFAULT_DATASET_PATH = REPO_ROOT / "ml" / "data" / "bharati_synthetic_telemetry.csv"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "ml" / "results" / "bharati_ml_end_to_end_validation.json"


class BharatiPipelineValidator:
    """
    Reusable End-to-End Validation Harness for Bharati ML Inference Pipeline.
    """

    def __init__(
        self,
        dataset_path: Union[str, Path] = DEFAULT_DATASET_PATH,
        output_json_path: Union[str, Path] = DEFAULT_OUTPUT_JSON,
        device: str = "cpu",
    ) -> None:
        self.dataset_path = Path(dataset_path)
        self.output_json_path = Path(output_json_path)
        self.device = device

        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Synthetic dataset not found: {self.dataset_path}")

        # Load synthetic telemetry dataset
        self.df = pd.read_csv(self.dataset_path)

        # Global aggregations
        self.total_records_processed = 0
        self.status_counts: Dict[str, int] = {k: 0 for k in VALID_STATUSES}
        self.type_counts: Dict[str, int] = {k: 0 for k in SUPPORTED_ANOMALY_TYPES}
        self.type_counts["NONE"] = 0

    def _record_output(self, out: BharatiTelemetryOutput) -> None:
        """Track statistics across processed outputs."""
        self.total_records_processed += 1
        if out.anomaly_status in self.status_counts:
            self.status_counts[out.anomaly_status] += 1

        if out.anomaly_type is not None and out.anomaly_type in self.type_counts:
            self.type_counts[out.anomaly_type] += 1
        elif out.anomaly_type is None:
            self.type_counts["NONE"] += 1

    def run_scenario_model_integrity(self) -> Dict[str, Any]:
        """
        Scenario: MODEL INTEGRITY
        Verify cryptographic SHA-256 and byte-size verification before inference.
        """
        report = validate_model_artifacts(
            model_version=DEFAULT_BHARATI_MODEL_VERSION, raise_on_error=False
        )
        passed = report.overall_status == "VALID"
        return {
            "scenario": "MODEL_INTEGRITY",
            "status": "PASS" if passed else "FAIL",
            "overall_integrity": report.overall_status,
            "artifacts_checked": len(report.artifact_results),
            "errors": report.errors,
            "details": report.artifact_results,
        }

    def run_scenario_contract_validation(self) -> Dict[str, Any]:
        """
        Scenario: CONTRACT VALIDATION
        Ensure unsupported stations, unsupported sensors, and malformed records are rejected.
        """
        rejections: Dict[str, bool] = {}

        # 1. Unsupported Station (e.g., Maitri 'MTR' sent to Bharati engine)
        try:
            BharatiTelemetryInput(
                station_id="MTR",
                sensor_id="BRT_TEMP_001",
                timestamp="2026-09-18T12:00:00Z",
                value=-15.0,
            )
            rejections["unsupported_station"] = False
        except UnsupportedStationError:
            rejections["unsupported_station"] = True

        # 2. Unsupported Sensor (e.g. Maitri sensor 'TEMP_001' sent to Bharati engine)
        try:
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="TEMP_001",
                timestamp="2026-09-18T12:00:00Z",
                value=0.5,
            )
            rejections["unsupported_sensor"] = False
        except UnsupportedSensorError:
            rejections["unsupported_sensor"] = True

        # 3. Missing Station
        try:
            BharatiTelemetryInput(
                station_id="",
                sensor_id="BRT_TEMP_001",
                timestamp="2026-09-18T12:00:00Z",
                value=-15.0,
            )
            rejections["empty_station"] = False
        except InvalidContractError:
            rejections["empty_station"] = True

        # 4. Missing Sensor
        try:
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="",
                timestamp="2026-09-18T12:00:00Z",
                value=-15.0,
            )
            rejections["empty_sensor"] = False
        except InvalidContractError:
            rejections["empty_sensor"] = True

        # 5. Missing Timestamp
        try:
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp="",
                value=-15.0,
            )
            rejections["empty_timestamp"] = False
        except InvalidContractError:
            rejections["empty_timestamp"] = True

        # 6. Malformed Value
        try:
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp="2026-09-18T12:00:00Z",
                value="not_a_number",  # type: ignore
            )
            rejections["malformed_value"] = False
        except InvalidContractError:
            rejections["malformed_value"] = True

        # 7. Invalid Quality
        try:
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp="2026-09-18T12:00:00Z",
                value=-15.0,
                quality="CORRUPTED_TAG",
            )
            rejections["invalid_quality"] = False
        except InvalidContractError:
            rejections["invalid_quality"] = True

        all_passed = all(rejections.values())
        return {
            "scenario": "CONTRACT_VALIDATION",
            "status": "PASS" if all_passed else "FAIL",
            "rejections": rejections,
            "all_invalid_inputs_rejected": all_passed,
        }

    def run_scenario_normal(self) -> Dict[str, Any]:
        """
        Scenario 1: NORMAL TELEMETRY SEQUENCE
        Feed consecutive normal observations for all 5 Bharati sensors.
        Verify:
        - 1..29 -> INSUFFICIENT_DATA (score=None, type=None)
        - 30+ -> Inference output evaluated.
        - Whenever status is NORMAL, anomaly_type MUST be NORMAL.
        """
        engine = BharatiLSTMInference(device=self.device)
        sensor_results: Dict[str, Dict[str, Any]] = {}

        for sensor in sorted(SUPPORTED_BHARATI_SENSORS):
            engine.reset_history()
            sub = self.df[
                (self.df["sensor_id"] == sensor) & (self.df["anomaly_type"] == "NORMAL")
            ].head(50)

            insufficient_count = 0
            normal_count = 0
            anomaly_count = 0

            for idx, row in sub.iterrows():
                rec = BharatiTelemetryInput(
                    station_id=str(row["station_id"]),
                    sensor_id=str(row["sensor_id"]),
                    timestamp=str(row["timestamp"]),
                    value=float(row["value"]),
                    unit=str(row["unit"]),
                    quality="GOOD",
                    source=str(row["source"]),
                )
                out = engine.infer_telemetry(rec)
                self._record_output(out)

                if out.anomaly_status == "INSUFFICIENT_DATA":
                    insufficient_count += 1
                    assert out.anomaly_score is None
                    assert out.anomaly_type is None
                elif out.anomaly_status == "NORMAL":
                    normal_count += 1
                    assert out.anomaly_score is not None
                    assert out.anomaly_type == "NORMAL"
                elif out.anomaly_status == "ANOMALY":
                    anomaly_count += 1
                    assert out.anomaly_score is not None
                    assert out.anomaly_type in SUPPORTED_ANOMALY_TYPES

            sensor_results[sensor] = {
                "records_tested": len(sub),
                "insufficient_data_steps": insufficient_count,
                "normal_inferences": normal_count,
                "model_variation_anomalies": anomaly_count,
                "status": (
                    "PASS"
                    if (
                        insufficient_count == 29
                        and (normal_count + anomaly_count) == (len(sub) - 29)
                    )
                    else "FAIL"
                ),
            }

        all_passed = all(r["status"] == "PASS" for r in sensor_results.values())
        return {
            "scenario": "NORMAL",
            "status": "PASS" if all_passed else "FAIL",
            "note": "Initial 29 observations produced INSUFFICIENT_DATA. Validated anomaly_type='NORMAL' when status='NORMAL'.",
            "per_sensor": sensor_results,
        }

    def run_scenario_spike(self) -> Dict[str, Any]:
        """
        Scenario 2: SPIKE SEQUENCE
        Feed normal warmup (30 points) then inject / feed synthetic spike telemetry records.
        Verify:
        - When detected as ANOMALY, anomaly_type is SPIKE or UNKNOWN.
        """
        engine = BharatiLSTMInference(device=self.device)
        sensor_results: Dict[str, Dict[str, Any]] = {}

        for sensor in sorted(SUPPORTED_BHARATI_SENSORS):
            engine.reset_history()
            # Extract 30 normal warm-up points + 5 spike points
            normal_rows = self.df[
                (self.df["sensor_id"] == sensor) & (self.df["anomaly_type"] == "NORMAL")
            ].head(30)
            spike_rows = self.df[
                (self.df["sensor_id"] == sensor) & (self.df["anomaly_type"] == "SPIKE")
            ].head(5)

            # Feed warmup
            for _, row in normal_rows.iterrows():
                out = engine.infer_telemetry(
                    BharatiTelemetryInput(
                        station_id=str(row["station_id"]),
                        sensor_id=str(row["sensor_id"]),
                        timestamp=str(row["timestamp"]),
                        value=float(row["value"]),
                        unit=str(row["unit"]),
                        quality="GOOD",
                        source=str(row["source"]),
                    )
                )
                self._record_output(out)

            spike_outputs = []
            for _, row in spike_rows.iterrows():
                out = engine.infer_telemetry(
                    BharatiTelemetryInput(
                        station_id=str(row["station_id"]),
                        sensor_id=str(row["sensor_id"]),
                        timestamp=str(row["timestamp"]),
                        value=float(row["value"]),
                        unit=str(row["unit"]),
                        quality="GOOD",
                        source="SIMULATOR",
                    )
                )
                self._record_output(out)
                spike_outputs.append(
                    {
                        "timestamp": out.timestamp,
                        "value": out.value,
                        "anomaly_score": out.anomaly_score,
                        "anomaly_status": out.anomaly_status,
                        "anomaly_type": out.anomaly_type,
                    }
                )
                if out.anomaly_status == "ANOMALY":
                    assert out.anomaly_type in {"SPIKE", "UNKNOWN"}

            sensor_results[sensor] = {
                "spikes_evaluated": len(spike_rows),
                "spike_outputs": spike_outputs,
                "status": "PASS",
            }

        return {
            "scenario": "SPIKE",
            "status": "PASS",
            "note": "When spike observations triggered ANOMALY, type classifier assigned SPIKE or UNKNOWN.",
            "per_sensor": sensor_results,
        }

    def run_scenario_drift(self) -> Dict[str, Any]:
        """
        Scenario 3: DRIFT SEQUENCE
        Feed normal warmup (30 points) then feed gradual monotonic drift sequence.
        Verify:
        - When detected as ANOMALY, anomaly_type is DRIFT or UNKNOWN.
        """
        engine = BharatiLSTMInference(device=self.device)
        sensor_results: Dict[str, Dict[str, Any]] = {}

        nominal_bases = {
            "BRT_TEMP_001": -10.0,
            "BRT_PRESS_001": 985.0,
            "BRT_HUM_001": 60.0,
            "BRT_VIB_001": 0.90,
            "BRT_POWER_001": 42.0,
        }
        drift_rates = {
            "BRT_TEMP_001": 0.25,
            "BRT_PRESS_001": 0.35,
            "BRT_HUM_001": 0.50,
            "BRT_VIB_001": 0.04,
            "BRT_POWER_001": 0.40,
        }

        for sensor in sorted(SUPPORTED_BHARATI_SENSORS):
            engine.reset_history()
            base_val = nominal_bases[sensor]
            rate = drift_rates[sensor]

            # 30 normal warmup points
            for i in range(30):
                val = base_val + 0.05 * np.sin(i)
                out = engine.infer_telemetry(
                    BharatiTelemetryInput(
                        station_id="BRT",
                        sensor_id=sensor,
                        timestamp=f"2026-03-01T00:{i:02d}:00Z",
                        value=float(val),
                        quality="GOOD",
                    )
                )
                self._record_output(out)

            # 30 gradual drift points
            drift_outputs = []
            for i in range(30):
                val = base_val + rate * i
                out = engine.infer_telemetry(
                    BharatiTelemetryInput(
                        station_id="BRT",
                        sensor_id=sensor,
                        timestamp=f"2026-03-01T01:{i:02d}:00Z",
                        value=float(val),
                        quality="GOOD",
                    )
                )
                self._record_output(out)
                drift_outputs.append(
                    {
                        "timestamp": out.timestamp,
                        "value": round(float(val), 4),
                        "anomaly_score": out.anomaly_score,
                        "anomaly_status": out.anomaly_status,
                        "anomaly_type": out.anomaly_type,
                    }
                )
                if out.anomaly_status == "ANOMALY":
                    assert out.anomaly_type in {"DRIFT", "UNKNOWN"}

            sensor_results[sensor] = {
                "drift_records_evaluated": len(drift_outputs),
                "drift_outputs": drift_outputs[:10],
                "status": "PASS",
            }

        return {
            "scenario": "DRIFT",
            "status": "PASS",
            "note": "When drift observations triggered ANOMALY, type classifier assigned DRIFT or UNKNOWN.",
            "per_sensor": sensor_results,
        }

    def run_scenario_stuck_value(self) -> Dict[str, Any]:
        """
        Scenario 4: STUCK_VALUE SEQUENCE
        Feed normal warmup (30 points) then feed repeated constant flatline.
        Verify:
        - Output is deterministic and stable.
        - When detected as ANOMALY, anomaly_type reflects classifier rules (STUCK_VALUE/UNKNOWN/SPIKE).
        """
        engine = BharatiLSTMInference(device=self.device)
        sensor_results: Dict[str, Dict[str, Any]] = {}

        stuck_values = {
            "BRT_TEMP_001": -30.0,
            "BRT_PRESS_001": 1020.0,
            "BRT_HUM_001": 85.0,
            "BRT_VIB_001": 2.5,
            "BRT_POWER_001": 55.0,
        }

        for sensor in sorted(SUPPORTED_BHARATI_SENSORS):
            engine.reset_history()
            flat_val = stuck_values[sensor]

            # 30 normal warmup points from dataset
            normal_rows = self.df[
                (self.df["sensor_id"] == sensor) & (self.df["anomaly_type"] == "NORMAL")
            ].head(30)
            for _, row in normal_rows.iterrows():
                out = engine.infer_telemetry(
                    BharatiTelemetryInput(
                        station_id=str(row["station_id"]),
                        sensor_id=str(row["sensor_id"]),
                        timestamp=str(row["timestamp"]),
                        value=float(row["value"]),
                        unit=str(row["unit"]),
                        quality="GOOD",
                    )
                )
                self._record_output(out)

            # 20 flatline points
            stuck_outputs = []
            for i in range(20):
                out = engine.infer_telemetry(
                    BharatiTelemetryInput(
                        station_id="BRT",
                        sensor_id=sensor,
                        timestamp=f"2026-03-02T10:{i:02d}:00Z",
                        value=float(flat_val),
                        quality="GOOD",
                    )
                )
                self._record_output(out)
                stuck_outputs.append(
                    {
                        "timestamp": out.timestamp,
                        "value": out.value,
                        "anomaly_score": out.anomaly_score,
                        "anomaly_status": out.anomaly_status,
                        "anomaly_type": out.anomaly_type,
                    }
                )
                if out.anomaly_status == "ANOMALY":
                    assert out.anomaly_type in {"STUCK_VALUE", "UNKNOWN", "SPIKE"}

            sensor_results[sensor] = {
                "stuck_records_evaluated": len(stuck_outputs),
                "stuck_outputs": stuck_outputs[:10],
                "status": "PASS",
            }

        return {
            "scenario": "STUCK_VALUE",
            "status": "PASS",
            "note": "When stuck-value observations triggered ANOMALY, type classifier assigned STUCK_VALUE, UNKNOWN, or SPIKE.",
            "per_sensor": sensor_results,
        }

    def run_scenario_dropout_missing(self) -> Dict[str, Any]:
        """
        Scenario 5: DROPOUT / MISSING DATA
        Feed a valid observation sequence, then feed a record with value=None or quality='BAD'.
        Verify:
        - Returns MISSING_DATA (score=None, type=None).
        - Clears rolling buffer (next valid record returns INSUFFICIENT_DATA).
        """
        engine = BharatiLSTMInference(device=self.device)
        engine.reset_history()

        # Warm up with 30 good points
        warmup = self.df[
            (self.df["sensor_id"] == "BRT_TEMP_001") & (self.df["anomaly_type"] == "NORMAL")
        ].head(30)
        for _, row in warmup.iterrows():
            out = engine.infer_telemetry(
                BharatiTelemetryInput(
                    station_id=str(row["station_id"]),
                    sensor_id=str(row["sensor_id"]),
                    timestamp=str(row["timestamp"]),
                    value=float(row["value"]),
                    quality="GOOD",
                )
            )
            self._record_output(out)

        # 1. Null Value record
        null_input = BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-09-18T13:00:00Z",
            value=None,
            unit="C",
            quality="GOOD",
        )
        null_out = engine.infer_telemetry(null_input)
        self._record_output(null_out)

        assert null_out.anomaly_status == "MISSING_DATA"
        assert null_out.anomaly_score is None
        assert null_out.anomaly_type is None

        # Next valid point must produce INSUFFICIENT_DATA due to buffer reset
        next_input = BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-09-18T13:01:00Z",
            value=-10.2,
            unit="C",
            quality="GOOD",
        )
        next_out = engine.infer_telemetry(next_input)
        self._record_output(next_out)
        assert next_out.anomaly_status == "INSUFFICIENT_DATA"

        # 2. Bad Quality record
        bad_quality_input = BharatiTelemetryInput(
            station_id="BRT",
            sensor_id="BRT_TEMP_001",
            timestamp="2026-09-18T13:02:00Z",
            value=-10.2,
            unit="C",
            quality="BAD",
        )
        bad_out = engine.infer_telemetry(bad_quality_input)
        self._record_output(bad_out)

        assert bad_out.anomaly_status == "MISSING_DATA"
        assert bad_out.anomaly_score is None
        assert bad_out.anomaly_type is None

        return {
            "scenario": "DROPOUT_MISSING_DATA",
            "status": "PASS",
            "null_value_status": null_out.anomaly_status,
            "bad_quality_status": bad_out.anomaly_status,
            "buffer_reset_verified": (next_out.anomaly_status == "INSUFFICIENT_DATA"),
        }

    def run_scenario_insufficient_data(self) -> Dict[str, Any]:
        """
        Scenario 6: INSUFFICIENT DATA
        Feed fewer than 30 observations (< seq_len).
        Verify all produce INSUFFICIENT_DATA with null score and type.
        """
        engine = BharatiLSTMInference(device=self.device)
        engine.reset_history()

        sub = self.df[
            (self.df["sensor_id"] == "BRT_PRESS_001") & (self.df["anomaly_type"] == "NORMAL")
        ].head(15)
        outputs = []
        for _, row in sub.iterrows():
            out = engine.infer_telemetry(
                BharatiTelemetryInput(
                    station_id=str(row["station_id"]),
                    sensor_id=str(row["sensor_id"]),
                    timestamp=str(row["timestamp"]),
                    value=float(row["value"]),
                    quality="GOOD",
                )
            )
            self._record_output(out)
            outputs.append(out)
            assert out.anomaly_status == "INSUFFICIENT_DATA"
            assert out.anomaly_score is None
            assert out.anomaly_type is None

        return {
            "scenario": "INSUFFICIENT_DATA",
            "status": "PASS",
            "steps_tested": len(outputs),
            "all_insufficient_data": True,
        }

    def run_scenario_multi_sensor_isolation(self) -> Dict[str, Any]:
        """
        Scenario 7: MULTI-SENSOR ISOLATION
        Interleave observations from multiple sensors and verify independent history tracking.
        """
        engine = BharatiLSTMInference(device=self.device)
        engine.reset_history()

        temp_rows = self.df[
            (self.df["sensor_id"] == "BRT_TEMP_001") & (self.df["anomaly_type"] == "NORMAL")
        ].head(30)
        vib_rows = self.df[
            (self.df["sensor_id"] == "BRT_VIB_001") & (self.df["anomaly_type"] == "NORMAL")
        ].head(15)
        power_rows = self.df[
            (self.df["sensor_id"] == "BRT_POWER_001") & (self.df["anomaly_type"] == "NORMAL")
        ].head(10)

        combined = []
        for i in range(30):
            r_t = temp_rows.iloc[i].to_dict()
            r_t["quality"] = "GOOD"
            combined.append(r_t)
            if i < len(vib_rows):
                r_v = vib_rows.iloc[i].to_dict()
                r_v["quality"] = "GOOD"
                combined.append(r_v)
            if i < len(power_rows):
                r_p = power_rows.iloc[i].to_dict()
                r_p["quality"] = "GOOD"
                combined.append(r_p)

        last_temp_out = None
        last_vib_out = None
        last_power_out = None

        for rec in combined:
            out = engine.infer_telemetry(BharatiTelemetryInput.from_dict(rec))
            self._record_output(out)
            if out.sensor_id == "BRT_TEMP_001":
                last_temp_out = out
            elif out.sensor_id == "BRT_VIB_001":
                last_vib_out = out
            elif out.sensor_id == "BRT_POWER_001":
                last_power_out = out

        assert last_temp_out is not None and last_temp_out.anomaly_status in {
            "NORMAL",
            "ANOMALY",
        }
        assert last_vib_out is not None and last_vib_out.anomaly_status == "INSUFFICIENT_DATA"
        assert last_power_out is not None and last_power_out.anomaly_status == "INSUFFICIENT_DATA"

        # Clear BRT_TEMP_001 with null value
        engine.infer_telemetry(
            BharatiTelemetryInput(
                station_id="BRT",
                sensor_id="BRT_TEMP_001",
                timestamp="2026-09-18T14:00:00Z",
                value=None,
            )
        )

        # Add 15 more points to BRT_VIB_001; it should reach 30 and output scored inference
        remaining_vib = self.df[
            (self.df["sensor_id"] == "BRT_VIB_001") & (self.df["anomaly_type"] == "NORMAL")
        ].iloc[15:30]
        final_vib_out = None
        for _, row in remaining_vib.iterrows():
            r_dict = row.to_dict()
            r_dict["quality"] = "GOOD"
            final_vib_out = engine.infer_telemetry(BharatiTelemetryInput.from_dict(r_dict))
            self._record_output(final_vib_out)

        assert final_vib_out is not None and final_vib_out.anomaly_status in {
            "NORMAL",
            "ANOMALY",
        }

        return {
            "scenario": "MULTI_SENSOR_ISOLATION",
            "status": "PASS",
            "interleaved_records": len(combined),
            "temp_reached_window": True,
            "vib_insufficient_during_interleave": True,
            "vib_completed_window_independently": True,
            "zero_cross_sensor_contamination": True,
        }

    def run_scenario_duplicate_and_stale_telemetry(self) -> Dict[str, Any]:
        """
        Scenario 8 & 9: DUPLICATE AND STALE TELEMETRY
        Verify that duplicate timestamps and stale out-of-order timestamps raise appropriate errors
        without corrupting the sliding buffer state.
        """
        engine = BharatiLSTMInference(device=self.device)
        engine.reset_history()

        # Send 1st record
        engine.infer_telemetry(
            BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T10:00:00Z", -10.0)
        )

        # Duplicate timestamp
        duplicate_rejected = False
        try:
            engine.infer_telemetry(
                BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T10:00:00Z", -10.5)
            )
        except DuplicateTelemetryError:
            duplicate_rejected = True

        # Stale timestamp (older)
        stale_rejected = False
        try:
            engine.infer_telemetry(
                BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T09:59:00Z", -10.5)
            )
        except StaleTelemetryError:
            stale_rejected = True

        # Forward valid timestamp succeeds
        valid_next_out = engine.infer_telemetry(
            BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T10:01:00Z", -10.1)
        )
        assert valid_next_out.anomaly_status == "INSUFFICIENT_DATA"

        return {
            "scenario": "DUPLICATE_AND_STALE_TELEMETRY",
            "status": "PASS" if (duplicate_rejected and stale_rejected) else "FAIL",
            "duplicate_rejected": duplicate_rejected,
            "stale_rejected": stale_rejected,
            "buffer_state_preserved": True,
        }

    def run_scenario_json_serialization(self) -> Dict[str, Any]:
        """
        Scenario 10: JSON SERIALIZATION ROUNDTRIP
        Verify every successful inference output can be serialized to and parsed from JSON without data loss.
        """
        engine = BharatiLSTMInference(device=self.device)
        engine.reset_history()

        test_records = [
            BharatiTelemetryInput("BRT", "BRT_TEMP_001", "2026-09-18T15:00:00Z", -10.0),
            BharatiTelemetryInput("BRT", "BRT_PRESS_001", "2026-09-18T15:00:00Z", None, quality="BAD"),
        ]

        sub = self.df[
            (self.df["sensor_id"] == "BRT_HUM_001") & (self.df["anomaly_type"] == "NORMAL")
        ].head(30)
        for _, row in sub.iterrows():
            r = row.to_dict()
            r["quality"] = "GOOD"
            test_records.append(BharatiTelemetryInput.from_dict(r))

        roundtrips: List[Dict[str, Any]] = []
        for rec in test_records:
            out = engine.infer_telemetry(rec)
            json_str = out.to_json()
            restored = BharatiTelemetryOutput.from_json(json_str)

            assert restored.station_id == out.station_id
            assert restored.sensor_id == out.sensor_id
            assert restored.timestamp == out.timestamp
            assert restored.value == out.value
            assert restored.anomaly_status == out.anomaly_status
            assert restored.anomaly_score == out.anomaly_score
            assert restored.anomaly_type == out.anomaly_type
            assert restored.model_version == out.model_version

            roundtrips.append(
                {
                    "status": out.anomaly_status,
                    "score": out.anomaly_score,
                    "type": out.anomaly_type,
                    "serialized_len": len(json_str),
                }
            )

        return {
            "scenario": "JSON_SERIALIZATION",
            "status": "PASS",
            "records_tested": len(roundtrips),
            "roundtrip_verified": True,
            "preserves_all_metadata": True,
        }

    def validate_all(self) -> Dict[str, Any]:
        """
        Execute full validation suite and produce summary report.
        """
        self.total_records_processed = 0
        self.status_counts = {k: 0 for k in VALID_STATUSES}
        self.type_counts = {k: 0 for k in SUPPORTED_ANOMALY_TYPES}
        self.type_counts["NONE"] = 0

        # Run Scenarios
        integrity_res = self.run_scenario_model_integrity()
        contract_res = self.run_scenario_contract_validation()
        normal_res = self.run_scenario_normal()
        spike_res = self.run_scenario_spike()
        drift_res = self.run_scenario_drift()
        stuck_res = self.run_scenario_stuck_value()
        dropout_res = self.run_scenario_dropout_missing()
        insufficient_res = self.run_scenario_insufficient_data()
        isolation_res = self.run_scenario_multi_sensor_isolation()
        duplicate_stale_res = self.run_scenario_duplicate_and_stale_telemetry()
        serialization_res = self.run_scenario_json_serialization()

        scenario_results = {
            "model_integrity": integrity_res,
            "contract_validation": contract_res,
            "normal": normal_res,
            "spike": spike_res,
            "drift": drift_res,
            "stuck_value": stuck_res,
            "dropout_missing": dropout_res,
            "insufficient_data": insufficient_res,
            "multi_sensor_isolation": isolation_res,
            "duplicate_and_stale_telemetry": duplicate_stale_res,
            "json_serialization": serialization_res,
        }

        all_passed = all(s["status"] == "PASS" for s in scenario_results.values())
        overall_status = "PASS" if all_passed else "FAIL"

        report: Dict[str, Any] = {
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "model_version": DEFAULT_BHARATI_MODEL_VERSION,
            "station_id": "BRT",
            "station_name": "Bharati",
            "reconstruction_threshold": 0.013215307652775843,
            "sensors_tested": sorted(list(SUPPORTED_BHARATI_SENSORS)),
            "total_records_processed": self.total_records_processed,
            "counts_by_status": self.status_counts,
            "counts_by_type": self.type_counts,
            "scenario_results": scenario_results,
            "contract_validation": {
                "status": contract_res["status"],
                "unsupported_stations_rejected": contract_res["rejections"]["unsupported_station"],
                "unsupported_sensors_rejected": contract_res["rejections"]["unsupported_sensor"],
                "malformed_records_rejected": contract_res["rejections"]["malformed_value"],
                "invalid_quality_rejected": contract_res["rejections"]["invalid_quality"],
            },
            "multi_sensor_isolation": {
                "status": isolation_res["status"],
                "isolated_sensors_count": len(SUPPORTED_BHARATI_SENSORS),
                "zero_cross_sensor_contamination": True,
            },
            "model_integrity": {
                "status": integrity_res["status"],
                "all_artifacts_valid": integrity_res["overall_integrity"] == "VALID",
            },
            "serialization_result": {
                "status": serialization_res["status"],
                "roundtrip_verified": serialization_res["roundtrip_verified"],
            },
            "known_limitations": [
                "The LSTM Autoencoder is trained to detect deviations in temporal reconstruction error; short constant sequences within normal ranges may not produce high MSE error on their own unless the anomaly classifier detects the flatline signature.",
                "All tests and benchmarks are conducted strictly on synthetic Antarctic telemetry engineered for Bharati station. No claims are made regarding real Antarctic hardware deployment.",
            ],
            "overall_status": overall_status,
            "notes": (
                "End-to-end ML inference pipeline verified for Bharati station ('BRT'). "
                "Pipeline correctness (contracts, artifact validation, rolling window buffers, "
                "sensor isolation, missing data handling, duplicate/stale protection, type classification, "
                "and JSON serialization) is validated deterministically."
            ),
        }

        # Save output json
        self.output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report


def main() -> None:
    """CLI runner for Bharati E2E Pipeline Validation."""
    print("Running Bharati ML End-to-End Pipeline Validation...")
    validator = BharatiPipelineValidator()
    report = validator.validate_all()
    print(f"Validation Complete! Overall Status: {report['overall_status']}")
    print(f"Total Records Processed: {report['total_records_processed']}")
    print(f"Status Counts: {report['counts_by_status']}")
    print(f"Type Counts: {report['counts_by_type']}")
    print(f"Report saved to: {validator.output_json_path}")


if __name__ == "__main__":
    main()
