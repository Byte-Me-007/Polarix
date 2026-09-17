"""
Production-Oriented ML Inference Layer for Polarix Maitri LSTM Autoencoder (SIH26060).

Features:
- Single-point and sliding window inference interface for backend integration.
- Independent, isolated rolling history buffers per (station_id, sensor_id).
- Strict handling of streaming states:
  - INSUFFICIENT_DATA: History has < 30 observations.
  - MISSING_DATA: Incoming value is null/NaN or quality != "GOOD".
  - NORMAL / ANOMALY: Evaluated against frozen persisted threshold.
- Loads pre-trained model weights, configuration, scalers, and validation threshold once.
- Strictly deterministic, zero online retraining.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple, Union

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch

from ml.training.lstm_autoencoder import (
    MODEL_VERSION,
    LSTMAutoencoder,
    LSTMAutoencoderConfig,
)
from ml.training.prepare_sequences import SensorScaler, load_scalers

DEFAULT_MODEL_PATH = "ml/models/lstm-ae-v1.pt"
DEFAULT_CONFIG_PATH = "ml/models/lstm-ae-v1_config.json"
DEFAULT_SCALER_PATH = "ml/models/lstm-ae-v1_scaler.json"
DEFAULT_THRESHOLD_PATH = "ml/results/lstm_threshold.json"

VALID_STATUSES = ["NORMAL", "ANOMALY", "INSUFFICIENT_DATA", "MISSING_DATA"]


class LSTMAutoencoderInference:
    """
    Stateful and stateless inference service for Maitri LSTM Autoencoder.
    """

    def __init__(
        self,
        model_path: Union[str, Path] = DEFAULT_MODEL_PATH,
        config_path: Union[str, Path] = DEFAULT_CONFIG_PATH,
        scaler_path: Union[str, Path] = DEFAULT_SCALER_PATH,
        threshold_path: Union[str, Path] = DEFAULT_THRESHOLD_PATH,
        device: str = "cpu",
    ) -> None:
        self.device = torch.device(device)
        self.model_path = Path(model_path)
        self.config_path = Path(config_path)
        self.scaler_path = Path(scaler_path)
        self.threshold_path = Path(threshold_path)

        # 1. Load Model Config
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        self.config = LSTMAutoencoderConfig.from_dict(config_dict)
        self.model_version = self.config.model_version

        # 2. Load Model Architecture and Weights
        self.model = LSTMAutoencoder(self.config).to(self.device)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model weights not found: {self.model_path}")
        state_dict = torch.load(self.model_path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state_dict)
        self.model.eval()

        # 3. Load Scalers
        if not self.scaler_path.exists():
            raise FileNotFoundError(f"Scaler file not found: {self.scaler_path}")
        self.scalers = load_scalers(self.scaler_path)

        # 4. Load Persisted Threshold
        if not self.threshold_path.exists():
            raise FileNotFoundError(f"Threshold file not found: {self.threshold_path}")
        with open(self.threshold_path, "r", encoding="utf-8") as f:
            thresh_dict = json.load(f)
        self.threshold = float(thresh_dict["threshold"])

        # 5. Stateful Rolling Buffers keyed by (station_id, sensor_id)
        self._buffers: Dict[Tuple[str, str], Deque[float]] = {}

    def _get_buffer(self, station_id: str, sensor_id: str) -> Deque[float]:
        key = (station_id, sensor_id)
        if key not in self._buffers:
            self._buffers[key] = collections.deque(maxlen=self.config.seq_len)
        return self._buffers[key]

    def reset_history(
        self, station_id: Optional[str] = None, sensor_id: Optional[str] = None
    ) -> None:
        """Reset historical sliding window buffer for specific sensor or all sensors."""
        if station_id is not None and sensor_id is not None:
            key = (station_id, sensor_id)
            if key in self._buffers:
                self._buffers[key].clear()
        elif station_id is not None:
            keys_to_clear = [k for k in self._buffers.keys() if k[0] == station_id]
            for k in keys_to_clear:
                self._buffers[k].clear()
        else:
            self._buffers.clear()

    def infer_observation(
        self,
        station_id: str,
        sensor_id: str,
        timestamp: str,
        value: Optional[float],
        quality: str = "GOOD",
    ) -> Dict[str, Any]:
        """
        Stream a single telemetry record and return real-time anomaly inference.

        Parameters:
        -----------
        station_id : str
            e.g. 'MTR'
        sensor_id : str
            e.g. 'TEMP_001'
        timestamp : str
            ISO-8601 formatted timestamp
        value : Optional[float]
            Observed sensor measurement value or None
        quality : str
            Telemetry quality flag ('GOOD', 'BAD', 'MISSING', etc.)

        Returns:
        --------
        Dict[str, Any]: Standardized anomaly response contract.
        """
        buffer = self._get_buffer(station_id, sensor_id)

        # Handle Missing or Bad-Quality Telemetry
        if (
            value is None
            or (isinstance(value, (int, float)) and np.isnan(value))
            or quality != "GOOD"
        ):
            # Clear buffer on corrupted/missing observation to prevent contaminated sequence construction
            buffer.clear()
            return {
                "station_id": station_id,
                "sensor_id": sensor_id,
                "timestamp": timestamp,
                "anomaly_score": None,
                "anomaly_status": "MISSING_DATA",
                "model_version": self.model_version,
            }

        float_val = float(value)
        buffer.append(float_val)

        # Handle Insufficient Observations (< seq_len)
        if len(buffer) < self.config.seq_len:
            return {
                "station_id": station_id,
                "sensor_id": sensor_id,
                "timestamp": timestamp,
                "anomaly_score": None,
                "anomaly_status": "INSUFFICIENT_DATA",
                "model_version": self.model_version,
            }

        # Full Sequence Available (len == seq_len)
        window_arr = np.array(buffer, dtype=np.float32)
        return self._evaluate_window(station_id, sensor_id, timestamp, window_arr)

    def infer_window(
        self,
        station_id: str,
        sensor_id: str,
        timestamp: str,
        window_values: List[float],
    ) -> Dict[str, Any]:
        """
        Stateless inference on an explicit sequence of observations.

        Parameters:
        -----------
        station_id : str
            e.g. 'MTR'
        sensor_id : str
            e.g. 'TEMP_001'
        timestamp : str
            Timestamp corresponding to the end of the window.
        window_values : List[float]
            List of numerical observations.

        Returns:
        --------
        Dict[str, Any]: Standardized anomaly response contract.
        """
        if len(window_values) != self.config.seq_len:
            return {
                "station_id": station_id,
                "sensor_id": sensor_id,
                "timestamp": timestamp,
                "anomaly_score": None,
                "anomaly_status": "INSUFFICIENT_DATA",
                "model_version": self.model_version,
            }

        arr = np.array(window_values, dtype=np.float32)
        if np.isnan(arr).any():
            return {
                "station_id": station_id,
                "sensor_id": sensor_id,
                "timestamp": timestamp,
                "anomaly_score": None,
                "anomaly_status": "MISSING_DATA",
                "model_version": self.model_version,
            }

        return self._evaluate_window(station_id, sensor_id, timestamp, arr)

    def _evaluate_window(
        self,
        station_id: str,
        sensor_id: str,
        timestamp: str,
        window_arr: np.ndarray,
    ) -> Dict[str, Any]:
        """Normalize, execute model forward pass, and score against threshold."""
        if sensor_id not in self.scalers:
            raise KeyError(f"No fitted scaler found for sensor '{sensor_id}'.")

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

        score = round(float(mse), 6)
        status = "ANOMALY" if score > self.threshold else "NORMAL"

        return {
            "station_id": station_id,
            "sensor_id": sensor_id,
            "timestamp": timestamp,
            "anomaly_score": score,
            "anomaly_status": status,
            "model_version": self.model_version,
        }
