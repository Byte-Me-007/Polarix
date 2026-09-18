"""
Polarix Bharati ML Service Adapter (SIH26060 - Person C).

A lightweight, framework-independent service boundary exposing the Bharati ML anomaly
detection pipeline for downstream consumption by Person A (Backend) or other orchestrators.

Design Principles:
- Framework-Independent: Zero dependency on FastAPI, MQTT, SQLite, WebSockets, or UI code.
- Thin Orchestration: Reuses Bharati LSTM inference engine and frozen artifacts.
- Strict Contract Validation: Accepts and validates typed BharatiTelemetryInput, returns BharatiTelemetryOutput.
- Zero Online Training: Model weights, scalers, and thresholds remain strictly frozen.
- State Isolation: Maintains independent 30-observation sliding windows per sensor.
- Missing Data Safety: Resets sensor window on missing data or non-GOOD quality to prevent corruption.
- Chronological Integrity: Protects against duplicate and out-of-order telemetry.
- Observability & Structured Audit: Captures structured diagnostic audit records per inference call.
"""

from __future__ import annotations

import collections
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Union

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
    parse_iso_timestamp,
)
from ml.inference.bharati_lstm_inference import (
    DEFAULT_BHARATI_CONFIG_PATH,
    DEFAULT_BHARATI_MODEL_PATH,
    DEFAULT_BHARATI_SCALER_PATH,
    DEFAULT_BHARATI_THRESHOLD_PATH,
    BharatiLSTMInference,
)
from ml.inference.bharati_ml_observability import (
    BharatiInferenceAuditRecord,
    summarize_audit_records,
)


class BharatiMLService:
    """
    Backend-consumable ML service adapter for Bharati station telemetry anomaly detection.
    """

    def __init__(
        self,
        model_path: Union[str, Path] = DEFAULT_BHARATI_MODEL_PATH,
        config_path: Union[str, Path] = DEFAULT_BHARATI_CONFIG_PATH,
        scaler_path: Union[str, Path] = DEFAULT_BHARATI_SCALER_PATH,
        threshold_path: Union[str, Path] = DEFAULT_BHARATI_THRESHOLD_PATH,
        manifest_path: Optional[Union[str, Path]] = None,
        verify_manifest: bool = True,
        device: str = "cpu",
        max_diagnostics_history: int = 100,
    ) -> None:
        """
        Initialize the Bharati ML Service.

        Parameters:
        -----------
        model_path : Union[str, Path]
            Path to PyTorch model weights.
        config_path : Union[str, Path]
            Path to model configuration JSON.
        scaler_path : Union[str, Path]
            Path to fitted sensor scalers JSON.
        threshold_path : Union[str, Path]
            Path to validation-selected frozen threshold JSON.
        manifest_path : Optional[Union[str, Path]]
            Path to model manifest JSON for integrity validation.
        verify_manifest : bool
            Whether to verify cryptographic integrity of artifacts on initialization.
        device : str
            PyTorch compute device ('cpu' or 'cuda').
        max_diagnostics_history : int
            Maximum number of recent inference audit records to retain in memory (default: 100).
        """
        self.station_id = "BRT"
        self.supported_sensors = sorted(list(SUPPORTED_BHARATI_SENSORS))
        self.model_version = DEFAULT_BHARATI_MODEL_VERSION
        self._max_diagnostics_history = max(1, int(max_diagnostics_history))
        self._diagnostics: Deque[BharatiInferenceAuditRecord] = collections.deque(
            maxlen=self._max_diagnostics_history
        )

        # Instantiate the underlying validated inference engine
        self._engine = BharatiLSTMInference(
            model_path=model_path,
            config_path=config_path,
            scaler_path=scaler_path,
            threshold_path=threshold_path,
            manifest_path=manifest_path,
            verify_manifest=verify_manifest,
            device=device,
        )

    @property
    def threshold(self) -> float:
        """Get the frozen persisted anomaly decision threshold (0.013215307652775843)."""
        return self._engine.threshold

    @property
    def sequence_length(self) -> int:
        """Get the required window length for scored inference (30 observations)."""
        return self._engine.config.seq_len

    def _record_audit(self, record: BharatiInferenceAuditRecord) -> None:
        """Safely append an audit record to the bounded history deque."""
        self._diagnostics.append(record)

    def process_telemetry(
        self,
        telemetry: Union[BharatiTelemetryInput, Dict[str, Any]],
    ) -> BharatiTelemetryOutput:
        """
        Process incoming telemetry record through the Bharati ML anomaly detection pipeline.

        Parameters:
        -----------
        telemetry : Union[BharatiTelemetryInput, Dict[str, Any]]
            A valid BharatiTelemetryInput dataclass or equivalent dictionary.

        Returns:
        --------
        BharatiTelemetryOutput:
            Typed contract containing metadata, anomaly_score, anomaly_status, and model_version.

        Raises:
        -------
        UnsupportedStationError: If station_id is not 'BRT'.
        UnsupportedSensorError: If sensor_id is not among the supported Bharati sensors.
        InvalidContractError: If payload fails schema, type, or contract validation.
        DuplicateTelemetryError: If identical timestamp arrives twice for the same sensor.
        StaleTelemetryError: If out-of-order telemetry with older timestamp arrives.
        """
        t0 = time.perf_counter()
        raw_station: Optional[str] = None
        raw_sensor: Optional[str] = None
        raw_timestamp: str = datetime.now(timezone.utc).isoformat()
        input_value_present: bool = False
        input_quality: Optional[str] = None
        history_before: int = 0

        try:
            if isinstance(telemetry, dict):
                raw_station = telemetry.get("station_id")
                raw_sensor = telemetry.get("sensor_id")
                if "timestamp" in telemetry and isinstance(telemetry["timestamp"], str):
                    raw_timestamp = telemetry["timestamp"]
                if "value" in telemetry:
                    v = telemetry["value"]
                    input_value_present = v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))
                input_quality = telemetry.get("quality")
                telemetry_input = BharatiTelemetryInput.from_dict(telemetry)
            elif isinstance(telemetry, BharatiTelemetryInput):
                raw_station = telemetry.station_id
                raw_sensor = telemetry.sensor_id
                raw_timestamp = telemetry.timestamp
                v = telemetry.value
                input_value_present = v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))
                input_quality = telemetry.quality
                telemetry_input = telemetry
            else:
                raise InvalidContractError(
                    f"Expected BharatiTelemetryInput or dict, got {type(telemetry).__name__}"
                )

            raw_station = telemetry_input.station_id
            raw_sensor = telemetry_input.sensor_id
            raw_timestamp = telemetry_input.timestamp
            input_quality = telemetry_input.quality
            v = telemetry_input.value
            input_value_present = v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))

            # Validate station and sensor constraints explicitly
            if telemetry_input.station_id not in SUPPORTED_BHARATI_STATIONS:
                raise UnsupportedStationError(
                    f"Unsupported station '{telemetry_input.station_id}'. Supported stations: {sorted(SUPPORTED_BHARATI_STATIONS)}"
                )
            if telemetry_input.sensor_id not in SUPPORTED_BHARATI_SENSORS:
                raise UnsupportedSensorError(
                    f"Unsupported sensor '{telemetry_input.sensor_id}'. Supported sensors: {sorted(SUPPORTED_BHARATI_SENSORS)}"
                )

            history_before = len(self._engine._get_buffer(telemetry_input.station_id, telemetry_input.sensor_id))

            # Execute inference pipeline
            output = self._engine.infer_telemetry(telemetry_input)
            t_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
            history_after = len(self._engine._get_buffer(output.station_id, output.sensor_id))

            if output.anomaly_status == "INSUFFICIENT_DATA":
                event_type = "INSUFFICIENT_DATA"
                inference_eligible = False
                state_changed = (history_after != history_before) or (history_after > 0)
            elif output.anomaly_status == "MISSING_DATA":
                event_type = "MISSING_DATA"
                inference_eligible = False
                state_changed = (history_before > 0) or (history_after != history_before)
            else:
                event_type = "INFERENCE"
                inference_eligible = True
                state_changed = True

            audit_rec = BharatiInferenceAuditRecord(
                timestamp=output.timestamp,
                station_id=output.station_id,
                sensor_id=output.sensor_id,
                input_value_present=input_value_present,
                input_quality=input_quality,
                input_accepted=True,
                event_type=event_type,
                anomaly_status=output.anomaly_status,
                anomaly_type=output.anomaly_type,
                anomaly_score=output.anomaly_score,
                threshold=self.threshold,
                model_version=self.model_version,
                history_size_before=history_before,
                history_size_after=history_after,
                inference_eligible=inference_eligible,
                state_changed=state_changed,
                processing_time_ms=t_elapsed_ms,
            )
            self._record_audit(audit_rec)
            return output

        except DuplicateTelemetryError as e:
            t_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
            buf_len = (
                len(self._engine._get_buffer(raw_station, raw_sensor))
                if raw_station and raw_sensor and raw_station in SUPPORTED_BHARATI_STATIONS and raw_sensor in SUPPORTED_BHARATI_SENSORS
                else 0
            )
            audit_rec = BharatiInferenceAuditRecord(
                timestamp=raw_timestamp,
                station_id=raw_station,
                sensor_id=raw_sensor,
                input_value_present=input_value_present,
                input_quality=input_quality,
                input_accepted=False,
                event_type="DUPLICATE",
                threshold=self.threshold,
                model_version=self.model_version,
                history_size_before=buf_len,
                history_size_after=buf_len,
                inference_eligible=False,
                state_changed=False,
                processing_time_ms=t_elapsed_ms,
                error_code="DuplicateTelemetryError",
                rejection_reason=str(e),
            )
            self._record_audit(audit_rec)
            raise

        except StaleTelemetryError as e:
            t_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
            buf_len = (
                len(self._engine._get_buffer(raw_station, raw_sensor))
                if raw_station and raw_sensor and raw_station in SUPPORTED_BHARATI_STATIONS and raw_sensor in SUPPORTED_BHARATI_SENSORS
                else 0
            )
            audit_rec = BharatiInferenceAuditRecord(
                timestamp=raw_timestamp,
                station_id=raw_station,
                sensor_id=raw_sensor,
                input_value_present=input_value_present,
                input_quality=input_quality,
                input_accepted=False,
                event_type="STALE",
                threshold=self.threshold,
                model_version=self.model_version,
                history_size_before=buf_len,
                history_size_after=buf_len,
                inference_eligible=False,
                state_changed=False,
                processing_time_ms=t_elapsed_ms,
                error_code="StaleTelemetryError",
                rejection_reason=str(e),
            )
            self._record_audit(audit_rec)
            raise

        except (UnsupportedStationError, UnsupportedSensorError, InvalidContractError, ValueError) as e:
            t_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
            valid_ts = raw_timestamp if isinstance(raw_timestamp, str) and raw_timestamp.strip() else datetime.now(timezone.utc).isoformat()
            try:
                parse_iso_timestamp(valid_ts)
            except Exception:
                valid_ts = datetime.now(timezone.utc).isoformat()

            buf_len = (
                len(self._engine._get_buffer(raw_station, raw_sensor))
                if raw_station and raw_sensor and raw_station in SUPPORTED_BHARATI_STATIONS and raw_sensor in SUPPORTED_BHARATI_SENSORS
                else 0
            )
            audit_rec = BharatiInferenceAuditRecord(
                timestamp=valid_ts,
                station_id=raw_station,
                sensor_id=raw_sensor,
                input_value_present=input_value_present,
                input_quality=input_quality,
                input_accepted=False,
                event_type="INVALID_INPUT",
                threshold=self.threshold,
                model_version=self.model_version,
                history_size_before=buf_len,
                history_size_after=buf_len,
                inference_eligible=False,
                state_changed=False,
                processing_time_ms=t_elapsed_ms,
                error_code=type(e).__name__,
                rejection_reason=str(e),
            )
            self._record_audit(audit_rec)
            raise

        except Exception as e:
            t_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
            valid_ts = raw_timestamp if isinstance(raw_timestamp, str) and raw_timestamp.strip() else datetime.now(timezone.utc).isoformat()
            try:
                parse_iso_timestamp(valid_ts)
            except Exception:
                valid_ts = datetime.now(timezone.utc).isoformat()

            audit_rec = BharatiInferenceAuditRecord(
                timestamp=valid_ts,
                station_id=raw_station,
                sensor_id=raw_sensor,
                input_value_present=input_value_present,
                input_quality=input_quality,
                input_accepted=False,
                event_type="ERROR",
                threshold=self.threshold,
                model_version=self.model_version,
                history_size_before=0,
                history_size_after=0,
                inference_eligible=False,
                state_changed=False,
                processing_time_ms=t_elapsed_ms,
                error_code=type(e).__name__,
                rejection_reason=str(e),
            )
            self._record_audit(audit_rec)
            raise

    def process_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convenience method for dictionary-in, dictionary-out backend interactions.
        """
        output = self.process_telemetry(data)
        return output.to_dict()

    def process_json(self, json_str: str, indent: Optional[int] = None) -> str:
        """
        Convenience method for JSON-string-in, JSON-string-out interactions.
        """
        input_obj = BharatiTelemetryInput.from_json(json_str)
        output = self.process_telemetry(input_obj)
        return output.to_json(indent=indent)

    def reset_sensor(self, sensor_id: str) -> None:
        """
        Reset rolling historical sliding window and timestamp state for a specific sensor.

        Parameters:
        -----------
        sensor_id : str
            Sensor identifier to reset (must be a valid Bharati sensor).
        """
        if sensor_id not in SUPPORTED_BHARATI_SENSORS:
            raise UnsupportedSensorError(
                f"Cannot reset unsupported sensor '{sensor_id}'. Supported: {sorted(SUPPORTED_BHARATI_SENSORS)}"
            )
        self._engine.reset_history(station_id=self.station_id, sensor_id=sensor_id)

    def reset_all(self) -> None:
        """
        Reset all sensor rolling history buffers and timestamp states for Bharati station.
        """
        self._engine.reset_history(station_id=self.station_id)

    def get_buffer_length(self, sensor_id: str) -> int:
        """
        Get the current number of buffered observations for a given sensor.
        """
        if sensor_id not in SUPPORTED_BHARATI_SENSORS:
            raise UnsupportedSensorError(
                f"Cannot get buffer for unsupported sensor '{sensor_id}'. Supported: {sorted(SUPPORTED_BHARATI_SENSORS)}"
            )
        return len(self._engine._get_buffer(self.station_id, sensor_id))

    def get_last_diagnostic(self) -> Optional[BharatiInferenceAuditRecord]:
        """
        Get the most recent diagnostic audit record.
        """
        if not self._diagnostics:
            return None
        return self._diagnostics[-1]

    def get_last_audit_record(self) -> Optional[BharatiInferenceAuditRecord]:
        """Alias for get_last_diagnostic."""
        return self.get_last_diagnostic()

    def get_recent_diagnostics(
        self, limit: Optional[int] = None
    ) -> List[BharatiInferenceAuditRecord]:
        """
        Get a defensive copy list of recent diagnostic audit records up to limit.
        """
        records = list(self._diagnostics)
        if limit is not None and limit > 0:
            return records[-limit:]
        return records

    def get_recent_audit_records(
        self, limit: Optional[int] = None
    ) -> List[BharatiInferenceAuditRecord]:
        """Alias for get_recent_diagnostics."""
        return self.get_recent_diagnostics(limit=limit)

    def clear_diagnostics(self) -> None:
        """
        Clear the diagnostic audit history.
        """
        self._diagnostics.clear()

    def clear_audit_records(self) -> None:
        """Alias for clear_diagnostics."""
        self.clear_diagnostics()

    def get_diagnostics_summary(self) -> Dict[str, Any]:
        """
        Summarize all retained diagnostic audit records.
        """
        return summarize_audit_records(list(self._diagnostics))

    def get_service_info(self) -> Dict[str, Any]:
        """
        Return diagnostic metadata and status information about the Bharati ML service.
        """
        buffer_lengths = {
            sensor: len(self._engine._get_buffer(self.station_id, sensor))
            for sensor in self.supported_sensors
        }
        return {
            "service_name": "BharatiMLService",
            "station_id": self.station_id,
            "supported_sensors": self.supported_sensors,
            "model_version": self.model_version,
            "sequence_length": self.sequence_length,
            "reconstruction_threshold": self.threshold,
            "active_buffer_lengths": buffer_lengths,
            "diagnostics_count": len(self._diagnostics),
            "diagnostics_history_limit": self._max_diagnostics_history,
            "status": "READY",
        }
