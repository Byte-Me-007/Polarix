"""
Causal State Machine Decision Layer for Sensor ML V2 (Polarix SIH26060 - Person C).

Conceptual States:
    INITIAL
       ↓
    NORMAL (Clean / Stable Normal)
       ↓ (Score >= Threshold OR Multi-Sensor Corroborated OR Strong Physical Deviation)
    ACTIVE_ANOMALY
       ↓ (Telemetry returned to Baseline AND Score Decaying)
    RECOVERY

Safety & Causality Invariants:
1. Strictly Causal: Decisions at step t depend exclusively on observations <= t.
2. Isolated Anomaly Protection: High-confidence isolated spikes and multi-sensor events bypass recovery suppression.
3. Deterministic Anomaly Classifier Compatibility: STUCK_VALUE, DRIFT, and SPIKE are preserved.
4. Missing Data Safety: Null/missing observations emit MISSING_DATA and reset/maintain causal state without generating alarms.
5. Idempotent on Duplicate/Stale Data: Re-processing an identical timestamp does not falsely advance the causal state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from ml.experiments.sensor_v2.multivariate_context.multivariate_scoring_functions import (
    MultivariateTimestampRecord,
)

SUPPORTED_FINAL_STATES = {"INITIAL", "NORMAL", "ACTIVE_ANOMALY", "RECOVERY", "MISSING_DATA"}


@dataclass(frozen=True)
class StateMachineConfig:
    """Hyperparameters for causal state machine decision layer."""

    mode: str = "ref"  # 'ref' (Step 52), 'suppression', 'suppression_override', 'decay_override'
    base_threshold: float = 4.50
    recovery_window_steps: int = 30
    suppression_barrier: float = 1.35
    strong_isolated_override: float = 1.50
    z_bound_override: float = 2.00
    sensor_elev_threshold: float = 3.00

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CausalStationStateMachine:
    """
    Online, causal state-machine decision engine for station-level multivariate telemetry.
    """

    def __init__(self, config: StateMachineConfig) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        """Reset internal causal tracking state."""
        self.step_idx: int = 0
        self.current_state: str = "INITIAL"
        self.last_anomaly_step: int = -9999
        self.last_timestamp: Optional[str] = None
        self.last_score: float = 0.0
        self.history_scores: List[float] = []

    def process_step(
        self,
        record: MultivariateTimestampRecord,
        station_score: float,
    ) -> Tuple[int, str, Dict[str, Any]]:
        """
        Process a single causal station telemetry record at timestamp t.

        Returns:
        --------
        is_anomaly : int (0 or 1)
        inferred_state : str
        metadata : Dict[str, Any]
        """
        # 1. Missing Data Check
        if record.valid_sensor_count == 0 or len(record.normalized_sensor_scores) == 0:
            self.current_state = "MISSING_DATA"
            return 0, "MISSING_DATA", {"reason": "missing_data", "steps_since_last_anomaly": 9999}

        # 2. Idempotency / Duplicate Timestamp Check
        if self.last_timestamp is not None and record.timestamp == self.last_timestamp:
            # Stale duplicate telemetry: return previous decision without advancing step_idx
            return (
                1 if self.current_state == "ACTIVE_ANOMALY" else 0,
                self.current_state,
                {"reason": "duplicate_timestamp", "steps_since_last_anomaly": self.step_idx - self.last_anomaly_step},
            )

        self.step_idx += 1
        t = self.step_idx
        self.last_timestamp = record.timestamp
        s = float(station_score)
        self.history_scores.append(s)

        steps_since_anom = t - self.last_anomaly_step if self.last_anomaly_step > 0 else 9999

        # Extract cross-channel signals
        s_arr = np.array(list(record.normalized_sensor_scores.values()), dtype=float)
        n_elev = int(np.sum(s_arr > self.config.sensor_elev_threshold))
        max_z = float(np.max(np.abs(s_arr))) if len(s_arr) > 0 else 0.0

        th = self.config.base_threshold
        is_anom = 0
        state = "NORMAL"

        if self.config.mode == "ref":
            # Candidate A (Reference): Raw Step 52 threshold
            if s >= th:
                is_anom = 1
                state = "ACTIVE_ANOMALY"
                self.last_anomaly_step = t
            elif 1 <= steps_since_anom <= self.config.recovery_window_steps:
                state = "RECOVERY"
            else:
                state = "NORMAL"

        elif self.config.mode == "suppression":
            # Candidate B: Pure recovery suppression
            eff_th = th * self.config.suppression_barrier if (1 <= steps_since_anom <= self.config.recovery_window_steps) else th
            if s >= eff_th:
                is_anom = 1
                state = "ACTIVE_ANOMALY"
                self.last_anomaly_step = t
            elif 1 <= steps_since_anom <= self.config.recovery_window_steps:
                state = "RECOVERY"
            else:
                state = "NORMAL"

        elif self.config.mode == "suppression_override":
            # Candidate C: Recovery suppression with strong isolated-anomaly override
            if 1 <= steps_since_anom <= self.config.recovery_window_steps:
                is_strong = (s >= th * self.config.strong_isolated_override) or (n_elev >= 2) or (max_z > self.config.z_bound_override)
                eff_th = th if is_strong else (th * self.config.suppression_barrier)
                if s >= eff_th:
                    is_anom = 1
                    state = "ACTIVE_ANOMALY"
                    self.last_anomaly_step = t
                else:
                    state = "RECOVERY"
            else:
                if s >= th:
                    is_anom = 1
                    state = "ACTIVE_ANOMALY"
                    self.last_anomaly_step = t
                else:
                    state = "NORMAL"

        elif self.config.mode == "decay_override":
            # Candidate D: Recovery decay with strong isolated-anomaly override
            if 1 <= steps_since_anom <= self.config.recovery_window_steps:
                is_strong = (s >= th * self.config.strong_isolated_override) or (n_elev >= 2) or (max_z > self.config.z_bound_override)
                decay_factor = 1.0 if is_strong else max(0.20, float(np.exp(-0.05 * steps_since_anom)))
                eff_s = s * decay_factor
                if eff_s >= th:
                    is_anom = 1
                    state = "ACTIVE_ANOMALY"
                    self.last_anomaly_step = t
                else:
                    state = "RECOVERY"
            else:
                if s >= th:
                    is_anom = 1
                    state = "ACTIVE_ANOMALY"
                    self.last_anomaly_step = t
                else:
                    state = "NORMAL"

        else:
            raise ValueError(f"Unknown state machine mode: {self.config.mode}")

        self.current_state = state
        self.last_score = s

        meta = {
            "step_index": t,
            "station_score": s,
            "steps_since_last_anomaly": steps_since_anom,
            "n_elevated_sensors": n_elev,
            "max_normalized_z": max_z,
            "inferred_state": state,
        }

        return is_anom, state, meta


def run_state_machine_over_sequence(
    aligned_records: List[MultivariateTimestampRecord],
    scores: np.ndarray,
    config: StateMachineConfig,
) -> Tuple[np.ndarray, List[str], List[Dict[str, Any]]]:
    """
    Run the causal state machine over a synchronized station record sequence.
    """
    engine = CausalStationStateMachine(config)
    preds = []
    states = []
    metas = []

    for rec, s in zip(aligned_records, scores):
        is_anom, st, meta = engine.process_step(rec, float(s))
        preds.append(is_anom)
        states.append(st)
        metas.append(meta)

    return np.array(preds, dtype=int), states, metas
