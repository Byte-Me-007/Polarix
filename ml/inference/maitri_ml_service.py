"""
Polarix Maitri ML Service Adapter (SIH26060 - Person C).

A lightweight, framework-independent service boundary exposing the Maitri ML anomaly
detection pipeline for downstream consumption by Person A (Backend) or other orchestrators.

Design Principles:
- Framework-Independent: Zero dependency on FastAPI, MQTT, SQLite, WebSockets, or UI code.
- Thin Orchestration: Reuses existing LSTM inference, anomaly classifier, and model registry.
- Strict Contract Validation: Accepts and validates typed TelemetryInput, returns TelemetryInferenceOutput.
- Zero Online Training: Model weights, scalers, and thresholds remain strictly frozen.
- Artifact Integrity: Enforces cryptographic SHA-256 validation before loading artifacts.
- State Isolation: Maintains independent 30-observation sliding windows per sensor.
- Missing Data Safety: Resets sensor window on missing data or non-GOOD quality to prevent corruption.
- Chronological Integrity: Protects against duplicate and out-of-order telemetry.
"""

from __future__ import annotations

import collections
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Union

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.inference.inference_contract import (
    DEFAULT_MODEL_VERSION,
    SUPPORTED_SENSORS,
    SUPPORTED_STATIONS,
    VALID_STATUSES,
    DuplicateTelemetryError,
    InvalidContractError,
    StaleTelemetryError,
    TelemetryInferenceOutput,
    TelemetryInput,
    UnsupportedSensorError,
    UnsupportedStationError,
)
from ml.inference.inference_diagnostics import (
    InferenceDiagnosticRecord,
)
from ml.inference.lstm_inference import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_SCALER_PATH,
    DEFAULT_THRESHOLD_PATH,
    LSTMAutoencoderInference,
)
from ml.models.model_registry import (
    ModelIntegrityError,
    ModelManifestNotFoundError,
    ModelVersionMismatchError,
    ModelValidationReport,
)


class MaitriMLService:
    """
    Backend-consumable ML service adapter for Maitri station telemetry anomaly detection.
    """

    def __init__(
        self,
        model_path: Union[str, Path] = DEFAULT_MODEL_PATH,
        config_path: Union[str, Path] = DEFAULT_CONFIG_PATH,
        scaler_path: Union[str, Path] = DEFAULT_SCALER_PATH,
        threshold_path: Union[str, Path] = DEFAULT_THRESHOLD_PATH,
        manifest_path: Optional[Union[str, Path]] = None,
        verify_manifest: bool = True,
        device: str = "cpu",
        max_diagnostics_history: int = 100,
    ) -> None:
        """
        Initialize the Maitri ML Service.

        Parameters:
        -----------
        model_path : Union[str, Path]
            Path to PyTorch model weights.
        config_path : Union[str, Path]
            Path to model configuration JSON.
        scaler_path : Union[str, Path]
            Path to fitted sensor scalers JSON.
        threshold_path : Union[str, Path]
            Path to validation-selected threshold JSON.
        manifest_path : Optional[Union[str, Path]]
            Optional explicit path to model manifest JSON.
        verify_manifest : bool
            Whether to enforce SHA-256 checksum verification on startup.
        device : str
            PyTorch compute device ('cpu' or 'cuda').
        max_diagnostics_history : int
            Maximum number of recent inference diagnostic records to retain in memory (default: 100).
        """
        self.station_id = "MTR"
        self.supported_sensors = sorted(list(SUPPORTED_SENSORS))
        self.model_version = DEFAULT_MODEL_VERSION
        self._max_diagnostics_history = max(1, int(max_diagnostics_history))
        self._diagnostics: Deque[InferenceDiagnosticRecord] = collections.deque(
            maxlen=self._max_diagnostics_history
        )

        # Instantiate the underlying validated inference engine
        self._engine = LSTMAutoencoderInference(
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
        """Get the frozen persisted anomaly decision threshold."""
        return self._engine.threshold

    @property
    def sequence_length(self) -> int:
        """Get the required window length for scored inference (30 observations)."""
        return self._engine.config.seq_len

    def _record_diagnostic(self, record: InferenceDiagnosticRecord) -> None:
        """Safely append a diagnostic record to the bounded history deque."""
        self._diagnostics.append(record)

    def process_telemetry(
        self,
        telemetry: Union[TelemetryInput, Dict[str, Any]],
    ) -> TelemetryInferenceOutput:
        """
        Process incoming telemetry record through the ML anomaly detection pipeline.

        Parameters:
        -----------
        telemetry : Union[TelemetryInput, Dict[str, Any]]
            A valid TelemetryInput dataclass or equivalent dictionary.

        Returns:
        --------
        TelemetryInferenceOutput:
            Typed contract containing metadata, anomaly_score, anomaly_status, and anomaly_type.

        Raises:
        -------
        UnsupportedStationError: If station_id is not 'MTR'.
        UnsupportedSensorError: If sensor_id is not among the supported Maitri sensors.
        InvalidContractError: If payload fails schema, type, or contract validation.
        DuplicateTelemetryError: If identical timestamp arrives twice for the same sensor.
        StaleTelemetryError: If out-of-order telemetry with older timestamp arrives.
        """
        t0 = time.perf_counter()
        raw_station: Optional[str] = None
        raw_sensor: Optional[str] = None
        raw_timestamp: str = datetime.now(timezone.utc).isoformat()

        try:
            if isinstance(telemetry, dict):
                raw_station = telemetry.get("station_id")
                raw_sensor = telemetry.get("sensor_id")
                if "timestamp" in telemetry and isinstance(telemetry["timestamp"], str):
                    raw_timestamp = telemetry["timestamp"]
                telemetry_input = TelemetryInput.from_dict(telemetry)
            elif isinstance(telemetry, TelemetryInput):
                raw_station = telemetry.station_id
                raw_sensor = telemetry.sensor_id
                raw_timestamp = telemetry.timestamp
                telemetry_input = telemetry
            else:
                raise InvalidContractError(
                    f"Expected TelemetryInput or dict, got {type(telemetry).__name__}"
                )

            raw_station = telemetry_input.station_id
            raw_sensor = telemetry_input.sensor_id
            raw_timestamp = telemetry_input.timestamp

            # Validate station and sensor constraints explicitly
            if telemetry_input.station_id not in SUPPORTED_STATIONS:
                raise UnsupportedStationError(
                    f"Unsupported station '{telemetry_input.station_id}'. Supported stations: {sorted(SUPPORTED_STATIONS)}"
                )
            if telemetry_input.sensor_id not in SUPPORTED_SENSORS:
                raise UnsupportedSensorError(
                    f"Unsupported sensor '{telemetry_input.sensor_id}'. Supported sensors: {sorted(SUPPORTED_SENSORS)}"
                )

            # Execute inference pipeline
            output = self._engine.infer_telemetry(telemetry_input)
            t_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)

            # Determine diagnostic inference status
            if output.anomaly_status == "INSUFFICIENT_DATA":
                diag_status = "INSUFFICIENT_DATA"
            elif output.anomaly_status == "MISSING_DATA":
                diag_status = "MISSING_DATA"
            else:
                diag_status = "SUCCESS"

            current_buf_len = len(self._engine._get_buffer(output.station_id, output.sensor_id))

            diagnostic = InferenceDiagnosticRecord(
                timestamp=output.timestamp,
                station_id=output.station_id,
                sensor_id=output.sensor_id,
                inference_status=diag_status,
                anomaly_status=output.anomaly_status,
                anomaly_type=output.anomaly_type,
                anomaly_score=output.anomaly_score,
                threshold=self.threshold,
                model_version=self.model_version,
                buffer_length=current_buf_len,
                processing_time_ms=t_elapsed_ms,
            )
            self._record_diagnostic(diagnostic)
            return output

        except DuplicateTelemetryError as e:
            t_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
            buf_len = (
                len(self._engine._get_buffer(raw_station, raw_sensor))
                if raw_station and raw_sensor and raw_station in SUPPORTED_STATIONS and raw_sensor in SUPPORTED_SENSORS
                else None
            )
            self._record_diagnostic(
                InferenceDiagnosticRecord(
                    timestamp=raw_timestamp,
                    station_id=raw_station,
                    sensor_id=raw_sensor,
                    inference_status="REJECTED_DUPLICATE",
                    threshold=self.threshold,
                    model_version=self.model_version,
                    buffer_length=buf_len,
                    processing_time_ms=t_elapsed_ms,
                    error_message=str(e),
                )
            )
            raise

        except StaleTelemetryError as e:
            t_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
            buf_len = (
                len(self._engine._get_buffer(raw_station, raw_sensor))
                if raw_station and raw_sensor and raw_station in SUPPORTED_STATIONS and raw_sensor in SUPPORTED_SENSORS
                else None
            )
            self._record_diagnostic(
                InferenceDiagnosticRecord(
                    timestamp=raw_timestamp,
                    station_id=raw_station,
                    sensor_id=raw_sensor,
                    inference_status="REJECTED_STALE",
                    threshold=self.threshold,
                    model_version=self.model_version,
                    buffer_length=buf_len,
                    processing_time_ms=t_elapsed_ms,
                    error_message=str(e),
                )
            )
            raise

        except (UnsupportedStationError, UnsupportedSensorError, InvalidContractError, ValueError) as e:
            t_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
            self._record_diagnostic(
                InferenceDiagnosticRecord(
                    timestamp=raw_timestamp if isinstance(raw_timestamp, str) and raw_timestamp else datetime.now(timezone.utc).isoformat(),
                    station_id=raw_station,
                    sensor_id=raw_sensor,
                    inference_status="REJECTED_INVALID",
                    threshold=self.threshold,
                    model_version=self.model_version,
                    buffer_length=None,
                    processing_time_ms=t_elapsed_ms,
                    error_message=str(e),
                )
            )
            raise

        except Exception as e:
            t_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
            self._record_diagnostic(
                InferenceDiagnosticRecord(
                    timestamp=raw_timestamp if isinstance(raw_timestamp, str) and raw_timestamp else datetime.now(timezone.utc).isoformat(),
                    station_id=raw_station,
                    sensor_id=raw_sensor,
                    inference_status="ERROR",
                    threshold=self.threshold,
                    model_version=self.model_version,
                    buffer_length=None,
                    processing_time_ms=t_elapsed_ms,
                    error_message=str(e),
                )
            )
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
        input_obj = TelemetryInput.from_json(json_str)
        output = self.process_telemetry(input_obj)
        return output.to_json(indent=indent)

    def reset_sensor(self, sensor_id: str) -> None:
        """
        Reset rolling historical sliding window and timestamp state for a specific sensor.

        Parameters:
        -----------
        sensor_id : str
            Sensor identifier to reset (must be a valid Maitri sensor).
        """
        if sensor_id not in SUPPORTED_SENSORS:
            raise UnsupportedSensorError(
                f"Cannot reset unsupported sensor '{sensor_id}'. Supported: {sorted(SUPPORTED_SENSORS)}"
            )
        self._engine.reset_history(station_id=self.station_id, sensor_id=sensor_id)

    def reset_all(self) -> None:
        """
        Reset all sensor rolling history buffers and timestamp states for Maitri station.
        """
        self._engine.reset_history(station_id=self.station_id)

    def get_buffer_length(self, sensor_id: str) -> int:
        """
        Get the current number of buffered observations for a given sensor.
        """
        if sensor_id not in SUPPORTED_SENSORS:
            raise UnsupportedSensorError(
                f"Cannot get buffer for unsupported sensor '{sensor_id}'. Supported: {sorted(SUPPORTED_SENSORS)}"
            )
        return len(self._engine._get_buffer(self.station_id, sensor_id))

    def get_last_diagnostic(self) -> Optional[InferenceDiagnosticRecord]:
        """
        Get the most recent diagnostic audit record.
        """
        if not self._diagnostics:
            return None
        return self._diagnostics[-1]

    def get_recent_diagnostics(
        self, limit: Optional[int] = None
    ) -> List[InferenceDiagnosticRecord]:
        """
        Get a defensive copy list of recent diagnostic records up to limit.
        """
        records = list(self._diagnostics)
        if limit is not None and limit > 0:
            return records[-limit:]
        return records

    def clear_diagnostics(self) -> None:
        """
        Clear the diagnostic audit history.
        """
        self._diagnostics.clear()

    def get_service_info(self) -> Dict[str, Any]:
        """
        Return diagnostic metadata and status information about the ML service.
        """
        buffer_lengths = {
            sensor: len(self._engine._get_buffer(self.station_id, sensor))
            for sensor in self.supported_sensors
        }
        return {
            "service_name": "MaitriMLService",
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
