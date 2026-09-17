"""
Maitri Telemetry Anomaly Type Classifier (Polarix SIH26060 - Person C).

A transparent, deterministic, feature-based rule engine that categorizes
detected telemetry anomaly windows into explainable physical classes:
- SPIKE: Sudden, short-lived pulse or abrupt jump.
- DRIFT: Gradual, persistent directional shift/ramp across the window.
- STUCK_VALUE: Frozen/constant telemetry with near-zero local variance.
- NORMAL: Standard stationary telemetry within normal parameters.
- UNKNOWN: Anomalous signal without clear singular archetype signature.

Design Principles:
- Zero dependency on FastAPI, Pydantic, or external UI frameworks.
- Deterministic signal-processing heuristics (slopes, variance, jump ratios, run lengths).
- Zero ground truth anomaly labels used during inference.
- Handles missing (NaN) and short windows cleanly without raising unhandled errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

SUPPORTED_ANOMALY_TYPES = {"NORMAL", "SPIKE", "DRIFT", "STUCK_VALUE", "UNKNOWN"}

# Default sensor-specific noise std heuristics (used when sensor_id is supplied)
DEFAULT_SENSOR_NOISE_STD: Dict[str, float] = {
    "TEMP_001": 0.3,
    "PRESS_001": 0.5,
    "HUM_001": 0.8,
    "VIB_001": 0.05,
    "POWER_001": 0.4,
}


@dataclass(frozen=True)
class WindowFeatures:
    """Extracted statistical features for explainable anomaly classification."""

    seq_len: int
    mean: float
    std: float
    tail_std_10: float
    max_step_jump: float
    jump_ratio: float
    net_displacement: float
    total_variation: float
    trend_ratio: float
    linear_slope: float
    linear_r_value: float
    max_consecutive_near_stuck: int
    tail_consecutive_stuck: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq_len": self.seq_len,
            "mean": round(self.mean, 4),
            "std": round(self.std, 4),
            "tail_std_10": round(self.tail_std_10, 4),
            "max_step_jump": round(self.max_step_jump, 4),
            "jump_ratio": round(self.jump_ratio, 4),
            "net_displacement": round(self.net_displacement, 4),
            "total_variation": round(self.total_variation, 4),
            "trend_ratio": round(self.trend_ratio, 4),
            "linear_slope": round(self.linear_slope, 4),
            "linear_r_value": round(self.linear_r_value, 4),
            "max_consecutive_near_stuck": self.max_consecutive_near_stuck,
            "tail_consecutive_stuck": self.tail_consecutive_stuck,
        }


class AnomalyTypeClassifier:
    """
    Explainable signal classifier for 30-step telemetry windows.
    """

    def __init__(
        self,
        min_window_len: int = 30,
        stuck_tolerance: float = 1e-4,
        stuck_run_threshold: int = 8,
        drift_r_threshold: float = 0.70,
        drift_trend_ratio_threshold: float = 0.45,
        spike_jump_ratio_threshold: float = 3.5,
    ) -> None:
        self.min_window_len = min_window_len
        self.stuck_tolerance = stuck_tolerance
        self.stuck_run_threshold = stuck_run_threshold
        self.drift_r_threshold = drift_r_threshold
        self.drift_trend_ratio_threshold = drift_trend_ratio_threshold
        self.spike_jump_ratio_threshold = spike_jump_ratio_threshold

    def extract_features(self, window: Union[List[float], np.ndarray]) -> WindowFeatures:
        """Extract deterministic mathematical features from 30-step window."""
        arr = np.array(window, dtype=np.float64)
        n = len(arr)
        if n == 0:
            raise ValueError("Window cannot be empty.")
        if np.isnan(arr).any():
            raise ValueError("Window contains NaN values.")

        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))

        # Tail window (last 10 steps)
        tail_k = min(10, n)
        tail_std = float(np.std(arr[-tail_k:]))

        # First differences (consecutive step deltas)
        diffs = np.abs(np.diff(arr)) if n > 1 else np.array([0.0])
        max_step = float(np.max(diffs)) if len(diffs) > 0 else 0.0
        median_diff = float(np.median(diffs)) if len(diffs) > 0 else 1e-6
        jump_ratio = max_step / (median_diff + 1e-6)

        # Net displacement and total variation
        net_disp = float(abs(arr[-1] - arr[0]))
        total_var = float(np.sum(diffs))
        trend_ratio = net_disp / (total_var + 1e-6)

        # Linear regression slope and correlation coefficient
        if n >= 3:
            t = np.arange(n, dtype=np.float64)
            t_mean = float(np.mean(t))
            t_centered = t - t_mean
            arr_centered = arr - mean_val
            t_var = float(np.sum(t_centered**2))
            if t_var > 0 and std_val > 0:
                slope = float(np.sum(t_centered * arr_centered) / t_var)
                r_val = float(np.sum(t_centered * arr_centered) / (np.sqrt(t_var) * np.sqrt(np.sum(arr_centered**2))))
            else:
                slope = 0.0
                r_val = 0.0
        else:
            slope = 0.0
            r_val = 0.0

        # Count consecutive identical or near-stuck values
        max_stuck_run = 0
        current_run = 1
        for i in range(1, n):
            if abs(arr[i] - arr[i - 1]) <= self.stuck_tolerance:
                current_run += 1
                if current_run > max_stuck_run:
                    max_stuck_run = current_run
            else:
                current_run = 1

        # Count tail consecutive stuck run ending at arr[-1]
        tail_stuck_run = 1
        for i in range(n - 1, 0, -1):
            if abs(arr[i] - arr[i - 1]) <= self.stuck_tolerance:
                tail_stuck_run += 1
            else:
                break

        return WindowFeatures(
            seq_len=n,
            mean=mean_val,
            std=std_val,
            tail_std_10=tail_std,
            max_step_jump=max_step,
            jump_ratio=jump_ratio,
            net_displacement=net_disp,
            total_variation=total_var,
            trend_ratio=trend_ratio,
            linear_slope=slope,
            linear_r_value=r_val,
            max_consecutive_near_stuck=max_stuck_run,
            tail_consecutive_stuck=tail_stuck_run,
        )

    def classify(
        self,
        window: Union[List[float], np.ndarray],
        sensor_id: Optional[str] = None,
        is_known_anomaly: bool = True,
    ) -> str:
        """
        Classify telemetry window into: STUCK_VALUE, SPIKE, DRIFT, NORMAL, or UNKNOWN.

        Parameters:
        -----------
        window : List[float] or np.ndarray
            Sequence of observations (expected length 30).
        sensor_id : Optional[str]
            Sensor identifier for physical scale context.
        is_known_anomaly : bool
            Whether the window was flagged as an anomaly by the primary detector (e.g. LSTM).

        Returns:
        --------
        str: One of {"STUCK_VALUE", "SPIKE", "DRIFT", "NORMAL", "UNKNOWN"}.
        """
        if window is None or len(window) == 0:
            return "MISSING_DATA"

        arr = np.array(window, dtype=np.float64)
        if len(arr) < self.min_window_len:
            return "INSUFFICIENT_DATA"
        if np.isnan(arr).any():
            return "MISSING_DATA"

        feats = self.extract_features(arr)
        noise_std = DEFAULT_SENSOR_NOISE_STD.get(sensor_id or "", 0.3)

        # 1. STUCK_VALUE Check
        # Significant flatline at tail or across majority of window
        if (
            feats.tail_consecutive_stuck >= self.stuck_run_threshold
            or feats.max_consecutive_near_stuck >= 12
            or (feats.tail_std_10 <= self.stuck_tolerance and feats.max_consecutive_near_stuck >= 8)
        ):
            return "STUCK_VALUE"

        # 2. SPIKE Check
        # Sudden shock jump: high jump_ratio, max_step significantly larger than noise
        is_sudden_jump = (
            feats.jump_ratio >= self.spike_jump_ratio_threshold
            and feats.max_step_jump >= 2.5 * noise_std
        )
        has_isolated_pulse = (
            feats.max_step_jump >= 0.40 * feats.total_variation
            and feats.trend_ratio < 0.85
        )

        if is_sudden_jump or (has_isolated_pulse and feats.max_step_jump >= 3.0 * noise_std):
            # Verify it is not a pure smooth linear ramp
            if not (abs(feats.linear_r_value) >= 0.95 and feats.trend_ratio >= 0.80 and feats.jump_ratio < 2.5):
                return "SPIKE"

        # 3. DRIFT Check
        # Sustained monotonic linear trend across the 30-step window without extreme single jump
        has_strong_correlation = abs(feats.linear_r_value) >= self.drift_r_threshold
        has_consistent_trend = feats.trend_ratio >= self.drift_trend_ratio_threshold
        has_sustained_displacement = feats.net_displacement >= 1.8 * noise_std
        no_dominating_single_spike = feats.max_step_jump <= 0.50 * (feats.net_displacement + 1e-6)

        if (
            has_strong_correlation
            and has_consistent_trend
            and has_sustained_displacement
            and no_dominating_single_spike
        ):
            return "DRIFT"

        # 4. NORMAL vs UNKNOWN
        if not is_known_anomaly:
            return "NORMAL"

        return "UNKNOWN"
