"""
Production-Oriented ML Inference Engine for Polarix Bharati LSTM Autoencoder (SIH26060 - Person C).

Station: Bharati ('BRT')
Model Version: lstm-ae-bharati-v1

Features:
- Single-point and sliding window inference interface for backend integration.
- Strictly validated typed data contracts (BharatiTelemetryInput -> BharatiTelemetryOutput).
- Independent, isolated rolling history buffers per (station_id, sensor_id).
- Strict handling of streaming states:
  - INSUFFICIENT_DATA: History has < 30 observations.
  - MISSING_DATA: Incoming value is null, non-finite (NaN/inf), or quality != "GOOD". Buffer cleared.
  - NORMAL / ANOMALY: Evaluated against frozen validation-selected threshold (0.013215307652775843).
- Chronological ordering & deduplication protection:
  - Duplicate timestamps raise DuplicateTelemetryError without corrupting buffer.
  - Out-of-order timestamps raise StaleTelemetryError without corrupting buffer.
- Loads pre-trained model weights, configuration, scalers, and validation threshold once.
- Strictly deterministic, zero online retraining.
- Zero dependency on FastAPI, MQTT, or web frameworks.
"""

from __future__ import annotations

import collections
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple, Union

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch

from ml.inference.bharati_anomaly_type_classifier import (
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
    parse_iso_timestamp,
)
from ml.models.bharati_lstm_autoencoder import (
    MODEL_VERSION,
    STATION_ID,
    BharatiLSTMAutoencoder,
    BharatiLSTMConfig,
)
from ml.models.model_registry import (
    ModelIntegrityError,
    ModelManifestNotFoundError,
    validate_model_artifacts,
)
from ml.training.prepare_bharati_sequences import (
    BharatiSensorScaler,
    load_bharati_scalers,
)

DEFAULT_BHARATI_MODEL_PATH = "ml/models/lstm-ae-bharati-v1.pt"
DEFAULT_BHARATI_CONFIG_PATH = "ml/models/lstm-ae-bharati-v1_config.json"
DEFAULT_BHARATI_SCALER_PATH = "ml/models/lstm-ae-bharati-v1_scaler.json"
DEFAULT_BHARATI_THRESHOLD_PATH = "ml/results/bharati_lstm_threshold.json"
DEFAULT_BHARATI_MANIFEST_PATH = "ml/models/lstm-ae-bharati-v1_manifest.json"


class BharatiLSTMInference:
    """
    Stateful and stateless inference service for Bharati LSTM Autoencoder.
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
        self.device = torch.device(device)
        self.model_path = Path(model_path)
        self.config_path = Path(config_path)
        self.scaler_path = Path(scaler_path)
        self.threshold_path = Path(threshold_path)
        self.manifest_path = Path(manifest_path) if manifest_path is not None else None
        self.verify_manifest = verify_manifest

        # 0. Cryptographic Artifact Integrity Verification
        if self.verify_manifest:
            validate_model_artifacts(
                model_version=MODEL_VERSION,
                manifest_path=self.manifest_path,
                raise_on_error=True,
            )

        # 1. Load Model Config
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        self.config = BharatiLSTMConfig.from_dict(config_dict)
        self.model_version = self.config.model_version

        # 2. Load Model Architecture and Weights
        self.model = BharatiLSTMAutoencoder(self.config).to(self.device)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model weights not found: {self.model_path}")
        state_dict = torch.load(self.model_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state_dict)
        self.model.eval()

        # 3. Load Scalers
        if not self.scaler_path.exists():
            raise FileNotFoundError(f"Scaler file not found: {self.scaler_path}")
        self.scalers = load_bharati_scalers(self.scaler_path)

        # 4. Load Persisted Frozen Threshold
        if not self.threshold_path.exists():
            raise FileNotFoundError(f"Threshold file not found: {self.threshold_path}")
        with open(self.threshold_path, "r", encoding="utf-8") as f:
            thresh_dict = json.load(f)
        self.threshold = float(thresh_dict["threshold"])

        # 5. Stateful Rolling Buffers keyed by (station_id, sensor_id)
        self._buffers: Dict[Tuple[str, str], Deque[float]] = {}
        # Track last processed timestamp per (station_id, sensor_id)
        self._last_timestamps: Dict[Tuple[str, str], datetime] = {}

        # 6. Anomaly Type Classifier
        self.type_classifier = BharatiAnomalyTypeClassifier(min_window_len=self.config.seq_len)

    def _get_buffer(self, station_id: str, sensor_id: str) -> Deque[float]:
        key = (station_id, sensor_id)
        if key not in self._buffers:
            self._buffers[key] = collections.deque(maxlen=self.config.seq_len)
        return self._buffers[key]

    def reset_history(
        self, station_id: Optional[str] = None, sensor_id: Optional[str] = None
    ) -> None:
        """Reset historical sliding window buffer and timestamp tracking for specific sensor or all sensors."""
        if station_id is not None and sensor_id is not None:
            key = (station_id, sensor_id)
            if key in self._buffers:
                self._buffers[key].clear()
            self._last_timestamps.pop(key, None)
        elif station_id is not None:
            keys_to_clear = [k for k in self._buffers.keys() if k[0] == station_id]
            for k in keys_to_clear:
                self._buffers[k].clear()
                self._last_timestamps.pop(k, None)
        else:
            self._buffers.clear()
            self._last_timestamps.clear()

    def infer_telemetry(
        self, telemetry: Union[BharatiTelemetryInput, Dict[str, Any]]
    ) -> BharatiTelemetryOutput:
        """
        Process a structured BharatiTelemetryInput observation and return a typed BharatiTelemetryOutput contract.
        """
        if isinstance(telemetry, dict):
            input_obj = BharatiTelemetryInput.from_dict(telemetry)
        elif isinstance(telemetry, BharatiTelemetryInput):
            input_obj = telemetry
        else:
            raise InvalidContractError(
                f"Expected BharatiTelemetryInput or dict, got {type(telemetry).__name__}"
            )

        if input_obj.station_id not in SUPPORTED_BHARATI_STATIONS:
            raise UnsupportedStationError(
                f"Unsupported station '{input_obj.station_id}'. Supported stations: {sorted(SUPPORTED_BHARATI_STATIONS)}"
            )
        if input_obj.sensor_id not in SUPPORTED_BHARATI_SENSORS:
            raise UnsupportedSensorError(
                f"Unsupported sensor '{input_obj.sensor_id}'. Supported sensors: {sorted(SUPPORTED_BHARATI_SENSORS)}"
            )

        key = (input_obj.station_id, input_obj.sensor_id)
        buffer = self._get_buffer(input_obj.station_id, input_obj.sensor_id)

        # 1. Handle Non-Finite (NaN, Inf, -Inf), Null, or Bad-Quality Telemetry
        is_invalid_value = (
            input_obj.value is None
            or not np.isfinite(input_obj.value)
        )
        if is_invalid_value or input_obj.quality != "GOOD":
            buffer.clear()
            self._last_timestamps.pop(key, None)
            return BharatiTelemetryOutput(
                station_id=input_obj.station_id,
                sensor_id=input_obj.sensor_id,
                timestamp=input_obj.timestamp,
                value=input_obj.value,
                unit=input_obj.unit,
                quality=input_obj.quality,
                source=input_obj.source,
                anomaly_score=None,
                anomaly_status="MISSING_DATA",
                model_version=self.model_version,
            )

        # 2. Chronological Ordering & Deduplication Check
        current_dt = parse_iso_timestamp(input_obj.timestamp)
        last_dt = self._last_timestamps.get(key)
        if last_dt is not None:
            if current_dt == last_dt:
                raise DuplicateTelemetryError(
                    f"Duplicate timestamp '{input_obj.timestamp}' received for sensor '{input_obj.sensor_id}'."
                )
            if current_dt < last_dt:
                raise StaleTelemetryError(
                    f"Stale out-of-order telemetry with timestamp '{input_obj.timestamp}' is older than last recorded '{last_dt.isoformat()}' for sensor '{input_obj.sensor_id}'."
                )

        # Update last processed timestamp and append to bounded buffer
        self._last_timestamps[key] = current_dt
        float_val = float(input_obj.value)
        buffer.append(float_val)

        # 3. Handle Insufficient Observations (< seq_len)
        if len(buffer) < self.config.seq_len:
            return BharatiTelemetryOutput(
                station_id=input_obj.station_id,
                sensor_id=input_obj.sensor_id,
                timestamp=input_obj.timestamp,
                value=input_obj.value,
                unit=input_obj.unit,
                quality=input_obj.quality,
                source=input_obj.source,
                anomaly_score=None,
                anomaly_status="INSUFFICIENT_DATA",
                model_version=self.model_version,
            )

        # 4. Full Sequence Available -> Scored Inference
        window_arr = np.array(buffer, dtype=np.float32)
        score, status = self._score_window_array(input_obj.sensor_id, window_arr)
        if status == "ANOMALY":
            anomaly_type = self.type_classifier.classify(
                window_arr, sensor_id=input_obj.sensor_id, is_known_anomaly=True
            )
        else:
            anomaly_type = "NORMAL"

        return BharatiTelemetryOutput(
            station_id=input_obj.station_id,
            sensor_id=input_obj.sensor_id,
            timestamp=input_obj.timestamp,
            value=input_obj.value,
            unit=input_obj.unit,
            quality=input_obj.quality,
            source=input_obj.source,
            anomaly_score=score,
            anomaly_status=status,
            anomaly_type=anomaly_type,
            model_version=self.model_version,
        )

    def infer_observation(
        self,
        station_id: str,
        sensor_id: str,
        timestamp: str,
        value: Optional[float],
        quality: str = "GOOD",
        unit: Optional[str] = None,
        source: Optional[str] = "SIMULATOR",
    ) -> BharatiTelemetryOutput:
        """
        Stream a single telemetry record and return real-time anomaly inference contract.
        Convenience wrapper around infer_telemetry.
        """
        telemetry = BharatiTelemetryInput(
            station_id=station_id,
            sensor_id=sensor_id,
            timestamp=timestamp,
            value=value,
            unit=unit,
            quality=quality,
            source=source,
        )
        return self.infer_telemetry(telemetry)

    def infer_window(
        self,
        station_id: str,
        sensor_id: str,
        timestamp: str,
        window_values: List[float],
        unit: Optional[str] = None,
        quality: str = "GOOD",
        source: Optional[str] = "SIMULATOR",
    ) -> BharatiTelemetryOutput:
        """
        Stateless inference on an explicit sequence of observations.
        """
        if station_id not in SUPPORTED_BHARATI_STATIONS:
            raise UnsupportedStationError(
                f"Unsupported station '{station_id}'. Supported stations: {sorted(SUPPORTED_BHARATI_STATIONS)}"
            )
        if sensor_id not in SUPPORTED_BHARATI_SENSORS:
            raise UnsupportedSensorError(
                f"Unsupported sensor '{sensor_id}'. Supported sensors: {sorted(SUPPORTED_BHARATI_SENSORS)}"
            )

        if len(window_values) != self.config.seq_len:
            return BharatiTelemetryOutput(
                station_id=station_id,
                sensor_id=sensor_id,
                timestamp=timestamp,
                value=window_values[-1] if window_values else None,
                unit=unit,
                quality=quality,
                source=source,
                anomaly_score=None,
                anomaly_status="INSUFFICIENT_DATA",
                anomaly_type=None,
                model_version=self.model_version,
            )

        arr = np.array(window_values, dtype=np.float32)
        if not np.all(np.isfinite(arr)) or quality != "GOOD":
            return BharatiTelemetryOutput(
                station_id=station_id,
                sensor_id=sensor_id,
                timestamp=timestamp,
                value=window_values[-1] if window_values else None,
                unit=unit,
                quality=quality,
                source=source,
                anomaly_score=None,
                anomaly_status="MISSING_DATA",
                anomaly_type=None,
                model_version=self.model_version,
            )

        score, status = self._score_window_array(sensor_id, arr)
        if status == "ANOMALY":
            anomaly_type = self.type_classifier.classify(
                arr, sensor_id=sensor_id, is_known_anomaly=True
            )
        else:
            anomaly_type = "NORMAL"

        return BharatiTelemetryOutput(
            station_id=station_id,
            sensor_id=sensor_id,
            timestamp=timestamp,
            value=float(window_values[-1]),
            unit=unit,
            quality=quality,
            source=source,
            anomaly_score=score,
            anomaly_status=status,
            anomaly_type=anomaly_type,
            model_version=self.model_version,
        )

    def _score_window_array(
        self,
        sensor_id: str,
        window_arr: np.ndarray,
    ) -> Tuple[float, str]:
        """Normalize window, execute model forward pass, and score against frozen threshold."""
        if sensor_id not in self.scalers:
            raise UnsupportedSensorError(f"No fitted scaler found for sensor '{sensor_id}'.")

        scaler = self.scalers[sensor_id]
        norm_window = scaler.transform(window_arr)

        # PyTorch Tensor: (batch=1, seq_len=30, input_size=1)
        x = (
            torch.from_numpy(norm_window)
            .float()
            .unsqueeze(0)
            .unsqueeze(-1)
            .to(self.device)
        )

        with torch.no_grad():
            reconstructed = self.model(x)
            mse = torch.mean((x - reconstructed) ** 2).item()

        score = float(mse)
        if not np.isfinite(score):
            score = 0.0

        # Classification: score > threshold -> ANOMALY, score <= threshold -> NORMAL
        status = "ANOMALY" if score > self.threshold else "NORMAL"
        return score, status
