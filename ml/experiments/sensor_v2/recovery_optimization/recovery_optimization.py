"""
Causal Recovery Decision Optimization Engine for Sensor ML V2 (SIH26060 - Person C).

Implements 5 Causal Decision Strategies:
1. Strategy A — Recovery Hysteresis (Dual-threshold stateful transition)
2. Strategy B — Causal Recovery Decay (Exponential temporal attenuation)
3. Strategy C — Multi-Sensor Confirmation (Cross-channel corroboration)
4. Strategy D — Recovery-Aware Station Score (Dynamic station-level modulation)
5. Strategy E — Temporal Persistence Filter (K-consecutive confirmation)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ml.experiments.sensor_v2.multivariate_context.multivariate_scoring_functions import (
    MultivariateTimestampRecord,
)


@dataclass(frozen=True)
class DecisionOptimizationConfig:
    """Hyperparameters for causal decision optimization strategies."""

    strategy: str  # 'hysteresis', 'decay', 'multisensor', 'station_modulation', 'persistence'
    base_threshold: float
    hysteresis_low_ratio: float = 0.60
    decay_lambda: float = 0.05
    single_sensor_barrier: float = 1.30
    recovery_modulation_factor: float = 0.65
    persistence_k: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def apply_recovery_hysteresis(
    scores: np.ndarray,
    th_high: float,
    th_low: Optional[float] = None,
    low_ratio: float = 0.60,
) -> np.ndarray:
    """
    Strategy A: Recovery Hysteresis.
    Requires th_high to enter ACTIVE_ANOMALY, and sustains anomaly state until score drops below th_low.
    """
    if th_low is None:
        th_low = float(th_high * low_ratio)

    preds = []
    in_anomaly = False
    for s in scores:
        if not in_anomaly:
            if s >= th_high:
                in_anomaly = True
                preds.append(1)
            else:
                preds.append(0)
        else:
            if s >= th_low:
                preds.append(1)
            else:
                in_anomaly = False
                preds.append(0)
    return np.array(preds, dtype=int)


def apply_causal_recovery_decay(
    aligned_records: List[MultivariateTimestampRecord],
    scores: np.ndarray,
    threshold: float,
    decay_lambda: float = 0.05,
    min_attenuation: float = 0.20,
) -> np.ndarray:
    """
    Strategy B: Causal Recovery Decay.
    Applies exponential decay over the elapsed steps since last detected anomaly.
    """
    adj_scores = np.copy(scores)
    last_anom_t = -9999
    last_score = 0.0

    for i, (rec, s) in enumerate(zip(aligned_records, scores)):
        delta_s = s - last_score
        steps_since = i - last_anom_t

        if s > threshold:
            last_anom_t = i
        elif 1 <= steps_since <= 30:
            decay = np.exp(-decay_lambda * steps_since)
            adj_scores[i] = s * max(min_attenuation, decay)

        last_score = s
    return np.array(adj_scores, dtype=float)


def apply_multisensor_confirmation(
    aligned_records: List[MultivariateTimestampRecord],
    scores: np.ndarray,
    base_threshold: float,
    sensor_elev_threshold: float = 3.0,
    single_sensor_barrier: float = 1.30,
) -> np.ndarray:
    """
    Strategy C: Multi-Sensor Confirmation.
    Requires higher confirmation threshold when only 1 channel is elevated in recovery.
    """
    preds = []
    for i, s in enumerate(scores):
        rec = aligned_records[i]
        s_arr = np.array(list(rec.normalized_sensor_scores.values()))
        n_elevated = int(np.sum(s_arr > sensor_elev_threshold))

        if n_elevated >= 2:
            eff_th = base_threshold
        else:
            eff_th = base_threshold * single_sensor_barrier

        preds.append(int(s >= eff_th))
    return np.array(preds, dtype=int)


def apply_recovery_aware_station_modulation(
    aligned_records: List[MultivariateTimestampRecord],
    scores: np.ndarray,
    threshold: float,
    modulation_factor: float = 0.65,
    sensor_elev_threshold: float = 3.0,
) -> np.ndarray:
    """
    Strategy D: Dynamic Station Score Modulation.
    Modulates station-level score when telemetry indicates an isolated recovering channel.
    """
    adj_scores = np.copy(scores)
    last_anom_t = -9999

    for i, (rec, s) in enumerate(zip(aligned_records, scores)):
        s_arr = np.array(list(rec.normalized_sensor_scores.values()))
        n_elevated = int(np.sum(s_arr > sensor_elev_threshold))
        steps_since = i - last_anom_t

        if s > threshold:
            last_anom_t = i
        elif 1 <= steps_since <= 30 and n_elevated <= 1:
            adj_scores[i] = s * modulation_factor

    return np.array(adj_scores, dtype=float)


from ml.experiments.sensor_v2.recovery_optimization.causal_persistence import (
    apply_causal_persistence,
)


def apply_temporal_persistence_filter(
    scores: np.ndarray,
    threshold: float,
    k: int = 2,
) -> np.ndarray:
    """
    Strategy E: Causal Temporal Persistence Filter.
    Emits an anomaly alarm at step t if and only if the threshold has been breached
    for at least K consecutive observations up to step t. Zero future lookahead.
    """
    return apply_causal_persistence(scores, threshold=threshold, k=k)
