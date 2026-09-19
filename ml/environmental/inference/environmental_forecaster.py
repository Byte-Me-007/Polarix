"""
Standalone Inference Module for Environmental Forecasting (Polarix SIH26060 - Person C).

Provides validated inference APIs for multivariate Antarctic environmental forecasting
(wind speed, barometric pressure, relative humidity) across horizons t+1h, t+6h, t+24h.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch

from ml.environmental.models.environmental_lstm import EnvironmentalLSTM
from ml.environmental.training.preprocessing import FEATURE_COLS, EnvironmentalFeatureScaler

logger = logging.getLogger("EnvironmentalForecaster")

VALID_STATION_IDS = {"MTR", "BRT"}
PROVENANCE_SOURCE = "SYNTHETIC_POLARIX_DATA"
PROVENANCE_DISCLAIMER = (
    "Generated deterministically from physically grounded Antarctic atmospheric transfer "
    "equations and seasonal solar geometry conditioned on NCPOR empirical bounds."
)


class EnvironmentalForecaster:
    """
    Station-aware multivariate environmental forecasting inference engine.

    Requires at least 24 consecutive hourly observations for the target station.
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        config_path: Optional[Union[str, Path]] = None,
        scaler_path: Optional[Union[str, Path]] = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent.parent / "models"
        self.model_path = Path(model_path) if model_path else base_dir / "environmental_lstm_v1.pt"
        self.config_path = Path(config_path) if config_path else base_dir / "environmental_lstm_v1_config.json"
        self.scaler_path = Path(scaler_path) if scaler_path else base_dir / "environmental_lstm_v1_scaler.json"

        # Load config
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found at {self.config_path}")
        with open(self.config_path, "r") as f:
            self.config = json.load(f)

        self.model_version = self.config.get("model_name", "environmental-lstm-v1")
        self.lookback = int(self.config.get("lookback_hours", 24))
        self.hidden_dim = int(self.config.get("hidden_dim", 64))
        self.num_layers = int(self.config.get("num_layers", 2))
        self.feature_cols = self.config.get("feature_cols", FEATURE_COLS)

        # Load scaler
        if not self.scaler_path.exists():
            raise FileNotFoundError(f"Scaler file not found at {self.scaler_path}")
        self.scaler = EnvironmentalFeatureScaler.load_json(self.scaler_path)

        # Load PyTorch model
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model weights not found at {self.model_path}")

        self.model = EnvironmentalLSTM(
            input_dim=len(self.feature_cols),
            hidden_dim=self.hidden_dim,
            num_layers=self.num_layers,
            output_dim=9,
            dropout=0.0,  # inference mode
        )
        state_dict = torch.load(self.model_path, map_location=torch.device("cpu"))
        self.model.load_state_dict(state_dict)
        self.model.eval()

    def _validate_telemetry_df(self, df: pd.DataFrame, station_id: str) -> Tuple[bool, Optional[str], Optional[pd.DataFrame]]:
        """
        Validates raw telemetry records for:
        - Allowed station_id
        - Required columns
        - Non-null, non-inf values
        - Timestamp chronological ordering & deduplication
        - Minimum continuous lookback requirement (at least 24 hours without gaps > 1h)
        """
        if station_id not in VALID_STATION_IDS:
            return False, f"Invalid station_id '{station_id}'. Must be one of {sorted(VALID_STATION_IDS)}", None

        required_cols = ["timestamp", "wind_speed_mps", "pressure_hpa", "humidity_percent", "temperature_c"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return False, f"Missing required telemetry columns: {missing}", None

        if len(df) == 0:
            return False, "Telemetry window is empty.", None

        # Check for NaN / Inf
        for col in required_cols:
            if df[col].isna().any():
                return False, f"Column '{col}' contains NaN values.", None
            if col != "timestamp":
                arr = df[col].to_numpy(dtype=float)
                if np.isinf(arr).any():
                    return False, f"Column '{col}' contains Inf values.", None

        # Process timestamps
        df_sorted = df.copy()
        try:
            df_sorted["dt"] = pd.to_datetime(df_sorted["timestamp"], utc=True)
        except Exception as e:
            return False, f"Failed to parse ISO-8601 timestamps: {str(e)}", None

        if df_sorted["dt"].duplicated().any():
            return False, "Telemetry contains duplicate timestamps.", None

        df_sorted = df_sorted.sort_values("dt").reset_index(drop=True)

        time_diffs = df_sorted["dt"].diff().dropna()
        if (time_diffs <= pd.Timedelta(0)).any():
            return False, "Timestamps are not strictly monotonically increasing.", None

        irregular_gaps = time_diffs > pd.Timedelta(hours=1, minutes=5)
        if irregular_gaps.any():
            return False, "Telemetry sequence contains time gaps exceeding 1 hour.", None

        if len(df_sorted) < self.lookback:
            return False, f"INSUFFICIENT_HISTORY: Required {self.lookback} hourly observations, got {len(df_sorted)}.", None

        # Ensure cyclical features exist or derive them causally from timestamp
        if "hour" not in df_sorted.columns:
            df_sorted["hour"] = df_sorted["dt"].dt.hour
        if "day_of_year" not in df_sorted.columns:
            df_sorted["day_of_year"] = df_sorted["dt"].dt.dayofyear
        if "sin_hour" not in df_sorted.columns:
            df_sorted["sin_hour"] = np.sin(2.0 * np.pi * df_sorted["hour"] / 24.0)
        if "cos_hour" not in df_sorted.columns:
            df_sorted["cos_hour"] = np.cos(2.0 * np.pi * df_sorted["hour"] / 24.0)
        if "sin_day" not in df_sorted.columns:
            df_sorted["sin_day"] = np.sin(2.0 * np.pi * df_sorted["day_of_year"] / 365.25)
        if "cos_day" not in df_sorted.columns:
            df_sorted["cos_day"] = np.cos(2.0 * np.pi * df_sorted["day_of_year"] / 365.25)

        df_sorted["station_id"] = station_id

        window_df = df_sorted.iloc[-self.lookback :].reset_index(drop=True)
        return True, None, window_df

    def predict_window(self, station_id: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Executes multivariate environmental forecast for the station given historical telemetry dataframe.
        """
        valid, err_msg, window_df = self._validate_telemetry_df(df, station_id)
        if not valid:
            status = "INSUFFICIENT_HISTORY" if "INSUFFICIENT_HISTORY" in str(err_msg) else "INVALID_INPUT"
            return {
                "station_id": station_id,
                "timestamp": df["timestamp"].iloc[-1] if len(df) > 0 and "timestamp" in df.columns else None,
                "status": status,
                "error_detail": err_msg,
                "model_version": self.model_version,
                "forecasts": None,
                "provenance": {
                    "source": PROVENANCE_SOURCE,
                    "model_status": "CANDIDATE",
                    "disclaimer": PROVENANCE_DISCLAIMER,
                },
            }

        X_features = self.scaler.transform_features(window_df)  # Shape (lookback, 9)
        X_tensor = torch.tensor(X_features, dtype=torch.float32).unsqueeze(0)  # (1, lookback, 9)

        with torch.no_grad():
            y_pred_norm = self.model(X_tensor).numpy()  # (1, 9)

        y_pred_denorm = self.scaler.inverse_transform_targets(y_pred_norm)[0]

        latest_ts = str(window_df["timestamp"].iloc[-1])

        return {
            "station_id": station_id,
            "timestamp": latest_ts,
            "status": "PREDICTION_AVAILABLE",
            "model_version": self.model_version,
            "forecasts": {
                "wind_speed_mps": {
                    "1h": round(max(0.0, float(y_pred_denorm[0])), 2),
                    "6h": round(max(0.0, float(y_pred_denorm[1])), 2),
                    "24h": round(max(0.0, float(y_pred_denorm[2])), 2),
                },
                "pressure_hpa": {
                    "1h": round(float(y_pred_denorm[3]), 1),
                    "6h": round(float(y_pred_denorm[4]), 1),
                    "24h": round(float(y_pred_denorm[5]), 1),
                },
                "humidity_percent": {
                    "1h": round(min(100.0, max(0.0, float(y_pred_denorm[6]))), 1),
                    "6h": round(min(100.0, max(0.0, float(y_pred_denorm[7]))), 1),
                    "24h": round(min(100.0, max(0.0, float(y_pred_denorm[8]))), 1),
                },
            },
            "provenance": {
                "source": PROVENANCE_SOURCE,
                "model_status": "CANDIDATE",
                "disclaimer": PROVENANCE_DISCLAIMER,
            },
        }

    def predict_dict(self, station_id: str, telemetry_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convenience wrapper accepting a list of telemetry dictionaries.
        """
        if not isinstance(telemetry_records, list):
            return {
                "station_id": station_id,
                "timestamp": None,
                "status": "INVALID_INPUT",
                "error_detail": "telemetry_records must be a list of dictionaries.",
                "model_version": self.model_version,
                "forecasts": None,
                "provenance": {
                    "source": PROVENANCE_SOURCE,
                    "model_status": "CANDIDATE",
                    "disclaimer": PROVENANCE_DISCLAIMER,
                },
            }
        df = pd.DataFrame(telemetry_records)
        return self.predict_window(station_id, df)

    def predict_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates rolling predictions across a continuous long-form telemetry dataframe.
        Appends prediction columns for each target.
        """
        df_out = df.copy()
        if "station_id" not in df_out.columns:
            raise ValueError("Dataframe must contain 'station_id' column.")

        pred_col_names = [
            "pred_wind_speed_1h_mps", "pred_wind_speed_6h_mps", "pred_wind_speed_24h_mps",
            "pred_pressure_1h_hpa", "pred_pressure_6h_hpa", "pred_pressure_24h_hpa",
            "pred_humidity_1h_percent", "pred_humidity_6h_percent", "pred_humidity_24h_percent",
        ]
        for col in pred_col_names:
            df_out[col] = np.nan

        stations = df_out["station_id"].unique()
        for st in stations:
            st_mask = df_out["station_id"] == st
            st_df = df_out[st_mask].sort_values("timestamp").reset_index(drop=False)

            if len(st_df) < self.lookback:
                continue

            X_feats = self.scaler.transform_features(st_df)
            n_windows = len(st_df) - self.lookback + 1

            X_seqs = np.zeros((n_windows, self.lookback, len(self.feature_cols)), dtype=np.float32)
            for i in range(n_windows):
                X_seqs[i] = X_feats[i : i + self.lookback]

            with torch.no_grad():
                preds_norm = self.model(torch.tensor(X_seqs, dtype=torch.float32)).numpy()

            preds_denorm = self.scaler.inverse_transform_targets(preds_norm)

            for i in range(n_windows):
                orig_idx = st_df.loc[i + self.lookback - 1, "index"]
                for p_idx, col in enumerate(pred_col_names):
                    val = float(preds_denorm[i, p_idx])
                    if "wind_speed" in col:
                        val = max(0.0, round(val, 2))
                    elif "pressure" in col:
                        val = round(val, 1)
                    elif "humidity" in col:
                        val = min(100.0, max(0.0, round(val, 1)))
                    df_out.loc[orig_idx, col] = val

        return df_out
