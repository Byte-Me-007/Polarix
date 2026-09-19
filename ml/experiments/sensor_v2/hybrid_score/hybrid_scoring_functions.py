"""
Hybrid Anomaly Scoring Formulations (Polarix SIH26060 - Person C).

Implements multi-component signal combination:
1. Current observation error: E_current(t) = (x_t - x_hat_t)^2
2. Recent transition error: E_delta(t) = ((x_t - x_{t-1}) - (x_hat_t - x_hat_{t-1}))^2
3. Bounded drift tracking: D_t = |mean(x_{t-K_recent+1:t}) - mean(x_{0:K_baseline})|
4. Validation-derived robust component normalization.
5. Hybrid Candidates:
   - H1: Current (0.7) + Delta (0.3)
   - H2: Current (0.7) + Drift (0.3)
   - H3: Current (0.5) + Delta (0.2) + Drift (0.3)
   - H4: Current (0.4) + Delta (0.1) + Drift (0.5)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


def compute_current_observation_error(x: np.ndarray, x_hat: np.ndarray) -> np.ndarray:
    """
    Squared error strictly at the final (current) timestep.
    Shape: (N, seq_len, 1) -> (N,) or (seq_len, 1) -> float.
    """
    if x.ndim == 2:
        return float((x[-1, 0] - x_hat[-1, 0]) ** 2)
    return np.array((x[:, -1, 0] - x_hat[:, -1, 0]) ** 2, dtype=float)


def compute_recent_transition_error(x: np.ndarray, x_hat: np.ndarray) -> np.ndarray:
    """
    Discrepancy between observed transition (x_t - x_{t-1}) and reconstructed transition.
    """
    if x.ndim == 2:
        delta_obs = x[-1, 0] - x[-2, 0]
        delta_rec = x_hat[-1, 0] - x_hat[-2, 0]
        return float((delta_obs - delta_rec) ** 2)

    delta_obs = x[:, -1, 0] - x[:, -2, 0]
    delta_rec = x_hat[:, -1, 0] - x_hat[:, -2, 0]
    return np.array((delta_obs - delta_rec) ** 2, dtype=float)


def compute_bounded_drift_signal(
    x: np.ndarray, k_recent: int = 5, k_baseline: int = 10
) -> np.ndarray:
    """
    Bounded short-term drift displacement comparing recent mean to sequence baseline mean.

    D_t = |mean(x_{t-k_recent+1 : t}) - mean(x_{0 : k_baseline})|
    """
    if x.ndim == 2:
        # x: (seq_len, 1)
        recent_mean = np.mean(x[-k_recent:, 0])
        base_mean = np.mean(x[:k_baseline, 0])
        return float(np.abs(recent_mean - base_mean))

    # x: (N, seq_len, 1)
    recent_mean = np.mean(x[:, -k_recent:, 0], axis=1)
    base_mean = np.mean(x[:, :k_baseline, 0], axis=1)
    return np.array(np.abs(recent_mean - base_mean), dtype=float)


@dataclass(frozen=True)
class HybridNormParameters:
    """Per-sensor or global robust scale reference parameters."""

    sensor_id: str
    ref_current: float
    ref_delta: float
    ref_drift: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def fit_hybrid_normalization_parameters(
    val_x: np.ndarray,
    val_x_hat: np.ndarray,
    val_metadata: List[Dict[str, Any]],
    k_recent: int = 5,
    k_baseline: int = 10,
) -> Dict[str, HybridNormParameters]:
    """
    Fit robust scale reference parameters strictly from clean normal validation windows.
    Reference statistic: median + 1.4826 * MAD (or P95 if MAD is near zero).
    """
    e_curr_all = compute_current_observation_error(val_x, val_x_hat)
    e_delta_all = compute_recent_transition_error(val_x, val_x_hat)
    d_drift_all = compute_bounded_drift_signal(val_x, k_recent=k_recent, k_baseline=k_baseline)

    # Group by sensor
    sensor_indices: Dict[str, List[int]] = {}
    for idx, meta in enumerate(val_metadata):
        # Strictly select clean normal windows
        if meta.get("window_state") == "CLEAN_NORMAL":
            s_id = meta["sensor_id"]
            if s_id not in sensor_indices:
                sensor_indices[s_id] = []
            sensor_indices[s_id].append(idx)

    norm_params: Dict[str, HybridNormParameters] = {}

    def get_robust_scale(arr: np.ndarray) -> float:
        if len(arr) == 0:
            return 1.0
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med)))
        scale = med + 1.4826 * mad
        if scale < 1e-5 or not np.isfinite(scale):
            scale = float(np.percentile(arr, 95)) if len(arr) > 0 else 1.0
        return max(scale, 1e-5)

    for sensor_id, indices in sensor_indices.items():
        sub_curr = e_curr_all[indices]
        sub_delta = e_delta_all[indices]
        sub_drift = d_drift_all[indices]

        norm_params[sensor_id] = HybridNormParameters(
            sensor_id=sensor_id,
            ref_current=get_robust_scale(sub_curr),
            ref_delta=get_robust_scale(sub_delta),
            ref_drift=get_robust_scale(sub_drift),
        )

    return norm_params


def normalize_and_combine_signals(
    x: np.ndarray,
    x_hat: np.ndarray,
    metadata: List[Dict[str, Any]],
    norm_params: Dict[str, HybridNormParameters],
    w_curr: float,
    w_delta: float,
    w_drift: float,
    k_recent: int = 5,
    k_baseline: int = 10,
) -> np.ndarray:
    """
    Calculate normalized hybrid score vector according to weights (w_curr, w_delta, w_drift).
    """
    e_curr = compute_current_observation_error(x, x_hat)
    e_delta = compute_recent_transition_error(x, x_hat)
    d_drift = compute_bounded_drift_signal(x, k_recent=k_recent, k_baseline=k_baseline)

    scores = []
    for idx, meta in enumerate(metadata):
        s_id = meta["sensor_id"]
        p = norm_params.get(
            s_id,
            HybridNormParameters(
                sensor_id=s_id,
                ref_current=1.0,
                ref_delta=1.0,
                ref_drift=1.0,
            ),
        )

        curr_norm = e_curr[idx] / p.ref_current
        delta_norm = e_delta[idx] / p.ref_delta
        drift_norm = d_drift[idx] / p.ref_drift

        score = w_curr * curr_norm + w_delta * delta_norm + w_drift * drift_norm
        scores.append(float(score))

    return np.array(scores, dtype=float)
