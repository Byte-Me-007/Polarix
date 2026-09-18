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
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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
)
from ml.inference.bharati_lstm_inference import (
    DEFAULT_BHARATI_CONFIG_PATH,
    DEFAULT_BHARATI_MODEL_PATH,
    DEFAULT_BHARATI_SCALER_PATH,
    DEFAULT_BHARATI_THRESHOLD_PATH,
    BharatiLSTMInference,
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
        """
        self.station_id = "BRT"
        self.supported_sensors = sorted(list(SUPPORTED_BHARATI_SENSORS))
        self.model_version = DEFAULT_BHARATI_MODEL_VERSION

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
        if isinstance(telemetry, dict):
            telemetry_input = BharatiTelemetryInput.from_dict(telemetry)
        elif isinstance(telemetry, BharatiTelemetryInput):
            telemetry_input = telemetry
        else:
            raise InvalidContractError(
                f"Expected BharatiTelemetryInput or dict, got {type(telemetry).__name__}"
            )

        # Validate station and sensor constraints explicitly
        if telemetry_input.station_id not in SUPPORTED_BHARATI_STATIONS:
            raise UnsupportedStationError(
                f"Unsupported station '{telemetry_input.station_id}'. Supported stations: {sorted(SUPPORTED_BHARATI_STATIONS)}"
            )
        if telemetry_input.sensor_id not in SUPPORTED_BHARATI_SENSORS:
            raise UnsupportedSensorError(
                f"Unsupported sensor '{telemetry_input.sensor_id}'. Supported sensors: {sorted(SUPPORTED_BHARATI_SENSORS)}"
            )

        # Execute inference pipeline
        return self._engine.infer_telemetry(telemetry_input)

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

    def get_service_info(self) -> Dict[str, Any]:
        """
        Return metadata and status information about the Bharati ML service.
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
            "status": "READY",
        }
