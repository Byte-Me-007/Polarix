"""
Rolling Z-Score Anomaly Detector for Polarix Bharati Telemetry (SIH26060 - Person C).

Implements an independent rolling-window statistical anomaly detector per Bharati sensor.
Features:
- Pure historical rolling statistics (no future leakage).
- Independent per-sensor baseline computation.
- Explicit dropout / missing data handling (status: MISSING_DATA).
- Safe interception of non-finite values (NaN, +inf, -inf).
- Deterministic anomaly scoring against configurable threshold.
- Model versioning tag ('zscore-bharati-v1').
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

MODEL_VERSION = "zscore-bharati-v1"
DEFAULT_WINDOW = 30
DEFAULT_MIN_PERIODS = 5
DEFAULT_THRESHOLD = 3.0
SUPPORTED_STATION = "BRT"

SUPPORTED_BHARATI_SENSORS = [
    "BRT_TEMP_001",
    "BRT_PRESS_001",
    "BRT_HUM_001",
    "BRT_VIB_001",
    "BRT_POWER_001",
]

REQUIRED_INPUT_COLUMNS = [
    "sensor_id",
    "timestamp",
    "value",
]

PREDICTION_COLUMNS = [
    "station_id",
    "sensor_id",
    "timestamp",
    "value",
    "unit",
    "quality",
    "source",
    "z_score",
    "anomaly_score",
    "predicted_status",
    "model_version",
]


@dataclass
class BharatiZScoreConfig:
    window: int = DEFAULT_WINDOW
    min_periods: int = DEFAULT_MIN_PERIODS
    threshold: float = DEFAULT_THRESHOLD
    model_version: str = MODEL_VERSION
    eps: float = 1e-8


class BharatiRollingZScoreDetector:
    """
    Rolling Z-Score Anomaly Detector for Bharati time-series telemetry.

    Computes trailing rolling mean and standard deviation for each sensor independently.
    Detects abnormal deviations where abs(z_score) > threshold.
    """

    def __init__(
        self,
        window: int = DEFAULT_WINDOW,
        min_periods: Optional[int] = None,
        threshold: float = DEFAULT_THRESHOLD,
        model_version: str = MODEL_VERSION,
        eps: float = 1e-8,
    ) -> None:
        if window < 2:
            raise ValueError(f"Rolling window must be >= 2, got {window}")
        if threshold <= 0:
            raise ValueError(f"Threshold must be positive, got {threshold}")

        if min_periods is None:
            effective_min_periods = min(DEFAULT_MIN_PERIODS, window)
        else:
            if min_periods < 1:
                raise ValueError(f"min_periods must be >= 1, got {min_periods}")
            effective_min_periods = min(min_periods, window)

        self.config = BharatiZScoreConfig(
            window=window,
            min_periods=effective_min_periods,
            threshold=threshold,
            model_version=model_version,
            eps=eps,
        )

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run rolling Z-score anomaly detection across all sensors in df.

        Parameters:
        -----------
        df : pd.DataFrame
            Input DataFrame containing telemetry. Must contain 'sensor_id', 'timestamp', 'value'.
            Must NOT rely on ground truth labels ('is_anomaly', 'anomaly_type').

        Returns:
        --------
        pd.DataFrame: Augmented DataFrame with z_score, anomaly_score, predicted_status, model_version.
        """
        for col in REQUIRED_INPUT_COLUMNS:
            if col not in df.columns:
                raise ValueError(f"Missing required input column '{col}' for Bharati Z-score detector.")

        # Work on a copy and sort chronologically per sensor
        working_df = df.copy()
        working_df["_orig_idx"] = np.arange(len(working_df))

        # Ensure timestamp is parsed for correct chronological sorting
        try:
            working_df["_parsed_ts"] = pd.to_datetime(working_df["timestamp"], format="ISO8601", utc=True)
        except Exception:
            working_df["_parsed_ts"] = pd.to_datetime(working_df["timestamp"], utc=True)
        working_df.sort_values(by=["sensor_id", "_parsed_ts"], inplace=True)

        sensor_results = []
        for sensor_id, sensor_group in working_df.groupby("sensor_id", sort=False):
            sensor_df = self._process_single_sensor(sensor_group)
            sensor_results.append(sensor_df)

        result_df = pd.concat(sensor_results, ignore_index=True)
        # Restore original order
        result_df.sort_values(by="_orig_idx", inplace=True)
        result_df.drop(columns=["_orig_idx", "_parsed_ts"], inplace=True)
        result_df.reset_index(drop=True, inplace=True)

        # Ensure standard schema order if columns are present
        cols_in_result = [c for c in PREDICTION_COLUMNS if c in result_df.columns]
        extra_cols = [c for c in result_df.columns if c not in PREDICTION_COLUMNS]
        return result_df[cols_in_result + extra_cols]

    def _process_single_sensor(self, group: pd.DataFrame) -> pd.DataFrame:
        """Process a single sensor's telemetry in strict chronological order."""
        res_group = group.copy()
        raw_vals = res_group["value"].to_numpy()
        n = len(raw_vals)

        # Sanitize numeric floats (handling non-numeric, infs, NaNs)
        numeric_vals = np.full(n, np.nan, dtype=float)
        for i in range(n):
            v = raw_vals[i]
            if v is not None and not pd.isna(v):
                try:
                    fv = float(v)
                    if math.isfinite(fv):
                        numeric_vals[i] = fv
                except (ValueError, TypeError):
                    pass

        z_scores = np.full(n, np.nan, dtype=float)
        anomaly_scores = np.full(n, np.nan, dtype=float)
        predicted_statuses = ["NORMAL"] * n

        # Trailing rolling window calculation
        val_series = pd.Series(numeric_vals)
        rolling_obj = val_series.rolling(
            window=self.config.window,
            min_periods=self.config.min_periods,
        )
        rolling_mean = rolling_obj.mean().to_numpy()
        rolling_std = rolling_obj.std(ddof=1).to_numpy()

        for i in range(n):
            val = numeric_vals[i]
            if np.isnan(val):
                # Explicit missing / non-finite / dropout telemetry
                z_scores[i] = np.nan
                anomaly_scores[i] = np.nan
                predicted_statuses[i] = "MISSING_DATA"
                continue

            r_mean = rolling_mean[i]
            r_std = rolling_std[i]

            if np.isnan(r_mean) or np.isnan(r_std) or r_std < self.config.eps:
                # Insufficient warmup period or zero variance
                z = 0.0
            else:
                z = (val - r_mean) / r_std

            score = abs(z)
            z_scores[i] = z
            anomaly_scores[i] = score

            if score > self.config.threshold:
                predicted_statuses[i] = "ANOMALY"
            else:
                predicted_statuses[i] = "NORMAL"

        res_group["z_score"] = z_scores
        res_group["anomaly_score"] = anomaly_scores
        res_group["predicted_status"] = predicted_statuses
        res_group["model_version"] = self.config.model_version

        return res_group
