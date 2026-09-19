"""
Causal Recovery-State Detector and Scoring Functions for Sensor ML V2 (Polarix SIH26060 - Person C).

Conceptual State Machine:
    INITIAL / UNKNOWN
           ↓
      CLEAN_NORMAL
           ↓ (Score > Threshold AND Z > Bound)
     ACTIVE_ANOMALY
           ↓ (Z <= Bound AND Score Decaying)
        RECOVERY (RECOVERY_NORMAL or RECOVERY_ANOMALOUS)
           ↓ (Steps > W_recovery OR Stable for K steps)
      STABLE_NORMAL

Guiding Principles:
1. Strictly Causal: At timestamp t, only telemetry up to t, prior inferred states, and prior scores are used.
2. Zero Ground-Truth Leakage: Inference-time state detection NEVER accesses ground-truth anomaly labels.
3. Safety: A recovery context does NOT automatically mean normal. If a new spike or persistent drift occurs during recovery,
   the detector immediately triggers ACTIVE_ANOMALY.
4. Robust Scaling: Baseline deviations (Z-scores) are computed relative to clean normal statistics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


SUPPORTED_RECOVERY_STATES = {
    "CLEAN_NORMAL",
    "ACTIVE_ANOMALY",
    "RECOVERY",
    "STABLE_NORMAL",
    "INSUFFICIENT_CONTEXT",
    "MISSING_DATA",
}


@dataclass(frozen=True)
class TelemetryPoint:
    """Telemetry observation at a single causal timestamp."""

    timestamp: str
    sensor_id: str
    raw_value: Optional[float]
    normalized_value: float
    base_anomaly_score: float
    is_missing: bool = False


@dataclass(frozen=True)
class RecoveryFeatures:
    """Causal features extracted at timestamp t for recovery-state tracking."""

    steps_since_last_anomaly: int
    recent_anomaly_count_w30: int
    recent_anomaly_duration: int
    current_score: float
    prev_score: float
    score_decay_rate: float
    baseline_z_deviation: float
    movement_toward_baseline: float
    recent_local_variance: float
    inferred_state: str
    attenuation_factor: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CausalRecoveryStateDetector:
    """
    Online, causal recovery-state detector for single telemetry channel streams.
    """

    def __init__(
        self,
        sensor_id: str,
        anomaly_threshold: float,
        z_norm_bound: float = 1.80,
        recovery_window_steps: int = 30,
        stable_confirm_steps: int = 5,
        decay_tolerance: float = 0.50,
        min_history_steps: int = 3,
    ) -> None:
        self.sensor_id = sensor_id
        self.anomaly_threshold = float(anomaly_threshold)
        self.z_norm_bound = float(z_norm_bound)
        self.recovery_window_steps = int(recovery_window_steps)
        self.stable_confirm_steps = int(stable_confirm_steps)
        self.decay_tolerance = float(decay_tolerance)
        self.min_history_steps = int(min_history_steps)

        self.reset()

    def reset(self) -> None:
        """Reset internal causal state tracking."""
        self.step_idx: int = 0
        self.current_state: str = "CLEAN_NORMAL"
        self.last_anomaly_step: int = -9999
        self.anomaly_start_step: int = -9999
        self.stable_normal_run: int = 0
        self.recent_anomalies: List[int] = []  # Step indices of anomalies in sliding window
        self.history_scores: List[float] = []
        self.history_z_vals: List[float] = []

    def process_step(self, point: TelemetryPoint) -> Tuple[RecoveryFeatures, float, str]:
        """
        Process a single causal telemetry observation.

        Returns:
        --------
        features : RecoveryFeatures
        adjusted_score : float
        inferred_state : str
        """
        self.step_idx += 1
        t = self.step_idx

        # 1. Missing data handling
        if point.is_missing or point.raw_value is None or np.isnan(point.normalized_value):
            self.current_state = "MISSING_DATA"
            feats = RecoveryFeatures(
                steps_since_last_anomaly=t - self.last_anomaly_step,
                recent_anomaly_count_w30=len(self.recent_anomalies),
                recent_anomaly_duration=0,
                current_score=0.0,
                prev_score=self.history_scores[-1] if len(self.history_scores) > 0 else 0.0,
                score_decay_rate=0.0,
                baseline_z_deviation=0.0,
                movement_toward_baseline=0.0,
                recent_local_variance=0.0,
                inferred_state="MISSING_DATA",
                attenuation_factor=1.0,
            )
            return feats, 0.0, "MISSING_DATA"

        s_t = float(point.base_anomaly_score)
        z_t = float(abs(point.normalized_value))
        prev_s = self.history_scores[-1] if len(self.history_scores) > 0 else s_t
        prev_z = self.history_z_vals[-1] if len(self.history_z_vals) > 0 else z_t

        delta_s = s_t - prev_s
        movement = prev_z - z_t  # Positive if moving toward baseline (0.0)

        self.history_scores.append(s_t)
        self.history_z_vals.append(z_t)

        # Prune recent anomalies older than recovery window
        self.recent_anomalies = [idx for idx in self.recent_anomalies if t - idx <= self.recovery_window_steps]

        steps_since_anom = t - self.last_anomaly_step if self.last_anomaly_step > 0 else 9999

        # Insufficient context check
        if t < self.min_history_steps:
            inferred = "INSUFFICIENT_CONTEXT"
            attenuation = 1.0
            adj_score = s_t
            self.current_state = inferred
            feats = RecoveryFeatures(
                steps_since_last_anomaly=steps_since_anom,
                recent_anomaly_count_w30=len(self.recent_anomalies),
                recent_anomaly_duration=0,
                current_score=s_t,
                prev_score=prev_s,
                score_decay_rate=delta_s,
                baseline_z_deviation=z_t,
                movement_toward_baseline=movement,
                recent_local_variance=0.0,
                inferred_state=inferred,
                attenuation_factor=attenuation,
            )
            return feats, adj_score, inferred

        # Local variance of last 5 z-scores
        recent_z_window = self.history_z_vals[-5:]
        local_var = float(np.var(recent_z_window)) if len(recent_z_window) > 1 else 0.0

        # State transition logic
        is_breaching_anomaly = (s_t > self.anomaly_threshold) and (z_t > self.z_norm_bound or delta_s > 0.5)

        if is_breaching_anomaly:
            # Active anomaly state
            if self.current_state != "ACTIVE_ANOMALY":
                self.anomaly_start_step = t
            self.current_state = "ACTIVE_ANOMALY"
            self.last_anomaly_step = t
            self.recent_anomalies.append(t)
            self.stable_normal_run = 0
            attenuation = 1.0
            adj_score = s_t
            inferred = "ACTIVE_ANOMALY"

        elif 1 <= steps_since_anom <= self.recovery_window_steps:
            # Within recovery window of a past anomaly
            if z_t <= self.z_norm_bound and delta_s <= self.decay_tolerance:
                # Value has returned within normal baseline bounds and score is not accelerating upward
                self.current_state = "RECOVERY"
                self.stable_normal_run += 1

                # Attenuation scaling: scales score down proportional to how close z_t is to clean baseline
                base_attenuation = max(0.10, min(1.0, (z_t / self.z_norm_bound) * 0.70))
                attenuation = base_attenuation
                adj_score = s_t * attenuation
                inferred = "RECOVERY"
            else:
                # Value is still elevated or re-escalating
                self.current_state = "RECOVERY"
                attenuation = 1.0
                adj_score = s_t
                inferred = "RECOVERY"

        else:
            # Beyond recovery window
            if z_t <= self.z_norm_bound:
                self.stable_normal_run += 1
                if self.stable_normal_run >= self.stable_confirm_steps:
                    self.current_state = "STABLE_NORMAL"
                else:
                    self.current_state = "CLEAN_NORMAL"
            else:
                self.current_state = "CLEAN_NORMAL"

            attenuation = 1.0
            adj_score = s_t
            inferred = self.current_state

        anom_duration = (t - self.anomaly_start_step + 1) if (self.current_state == "ACTIVE_ANOMALY" and self.anomaly_start_step > 0) else 0

        feats = RecoveryFeatures(
            steps_since_last_anomaly=steps_since_anom,
            recent_anomaly_count_w30=len(self.recent_anomalies),
            recent_anomaly_duration=anom_duration,
            current_score=s_t,
            prev_score=prev_s,
            score_decay_rate=delta_s,
            baseline_z_deviation=z_t,
            movement_toward_baseline=movement,
            recent_local_variance=local_var,
            inferred_state=inferred,
            attenuation_factor=attenuation,
        )

        return feats, adj_score, inferred


def apply_causal_recovery_detector_to_sequence(
    sensor_id: str,
    raw_values: List[Optional[float]],
    norm_values: np.ndarray,
    base_scores: np.ndarray,
    timestamps: List[str],
    threshold: float,
    z_norm_bound: float = 1.80,
    recovery_window_steps: int = 30,
) -> Tuple[np.ndarray, List[RecoveryFeatures], List[str]]:
    """
    Run causal recovery state detection along a single sensor's chronological sequence.
    """
    detector = CausalRecoveryStateDetector(
        sensor_id=sensor_id,
        anomaly_threshold=threshold,
        z_norm_bound=z_norm_bound,
        recovery_window_steps=recovery_window_steps,
    )

    adj_scores = []
    features_list = []
    inferred_states = []

    for i in range(len(timestamps)):
        pt = TelemetryPoint(
            timestamp=timestamps[i],
            sensor_id=sensor_id,
            raw_value=raw_values[i] if i < len(raw_values) else None,
            normalized_value=float(norm_values[i]),
            base_anomaly_score=float(base_scores[i]),
            is_missing=bool(raw_values[i] is None or np.isnan(norm_values[i])) if i < len(raw_values) else False,
        )
        feats, s_adj, state = detector.process_step(pt)
        adj_scores.append(s_adj)
        features_list.append(feats)
        inferred_states.append(state)

    return np.array(adj_scores, dtype=float), features_list, inferred_states
