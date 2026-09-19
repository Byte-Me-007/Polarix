"""
Multivariate Sensor-Context Fusion Scoring Functions (Polarix SIH26060 - Person C).

Implements station-level cross-sensor context aggregation:
1. Timestamp Alignment: Aligns all 5 station sensors along a synchronized chronological timeline.
2. Missing Data & Context Safety: Exposes explicit missing indicators and INSUFFICIENT_CONTEXT state.
3. Cross-Sensor Anomaly Signals:
   - A. Max-Sensor-Context: S_max(t) = max_{s in valid} S_norm,s(t)
   - B. Mean-Sensor-Context: S_mean(t) = (1/|valid|) * sum_{s in valid} S_norm,s(t)
   - C. Robust Aggregate: S_robust(t) = median(S_norm) + 0.5 * IQR(S_norm)
   - D. Agreement-Aware: S_agreement(t) = S_max(t) * (1 + 0.5 * N_elevated / |valid|)
   - E. Hybrid-Context: S_hybrid(t) = 0.7 * S_max(t) + 0.3 * S_mean_{s != top}(t)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MultivariateTimestampRecord:
    """Station-level aligned multi-sensor telemetry record at a single timestamp."""

    station_id: str
    timestamp: str
    sensor_ids: List[str]
    is_anomaly_station: int  # 1 if ANY sensor is anomalous at timestamp t, else 0
    window_state_station: str  # CLEAN_NORMAL, CONTAMINATED_NORMAL, ACTIVE_ANOMALY
    primary_anomaly_type: str
    missing_sensor_count: int
    valid_sensor_count: int
    normalized_sensor_scores: Dict[str, float]
    raw_sensor_values: Dict[str, Optional[float]]
    split: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def align_station_multivariate_windows(
    station_id: str,
    metadata_per_sensor: Dict[str, List[Dict[str, Any]]],
    norm_scores_per_sensor: Dict[str, np.ndarray],
    expected_sensors: List[str],
) -> List[MultivariateTimestampRecord]:
    """
    Align per-sensor evaluation windows chronologically by timestamp into synchronized station records.
    """
    # Map (sensor_id, timestamp) -> (meta, norm_score)
    ts_sensor_map: Dict[str, Dict[str, Tuple[Dict[str, Any], float]]] = {}

    for sensor_id, meta_list in metadata_per_sensor.items():
        scores = norm_scores_per_sensor.get(sensor_id, np.zeros(len(meta_list)))
        for meta, score in zip(meta_list, scores):
            ts = meta["timestamp"]
            if ts not in ts_sensor_map:
                ts_sensor_map[ts] = {}
            ts_sensor_map[ts][sensor_id] = (meta, float(score))

    # Sort timestamps chronologically
    sorted_timestamps = sorted(ts_sensor_map.keys())
    aligned_records: List[MultivariateTimestampRecord] = []

    for ts in sorted_timestamps:
        s_data = ts_sensor_map[ts]
        norm_scores: Dict[str, float] = {}
        raw_vals: Dict[str, Optional[float]] = {}
        anom_flags: List[int] = []
        window_states: List[str] = []
        anom_types: List[str] = []
        split_name = "val"

        for s_id in expected_sensors:
            if s_id in s_data:
                meta, score = s_data[s_id]
                norm_scores[s_id] = score
                raw_vals[s_id] = meta.get("target_value")
                anom_flags.append(meta.get("is_anomaly", 0))
                window_states.append(meta.get("window_state", "CLEAN_NORMAL"))
                a_type = meta.get("anomaly_type", "NORMAL")
                if a_type != "NORMAL":
                    anom_types.append(a_type)
                split_name = meta.get("split", split_name)
            else:
                raw_vals[s_id] = None

        valid_count = len(norm_scores)
        missing_count = len(expected_sensors) - valid_count

        # Station-level labels
        is_anom_station = 1 if any(f == 1 for f in anom_flags) else 0
        if is_anom_station == 1:
            station_state = "ACTIVE_ANOMALY"
        elif any(st == "CONTAMINATED_NORMAL" for st in window_states):
            station_state = "CONTAMINATED_NORMAL"
        else:
            station_state = "CLEAN_NORMAL"

        primary_type = anom_types[0] if len(anom_types) > 0 else "NORMAL"

        aligned_records.append(
            MultivariateTimestampRecord(
                station_id=station_id,
                timestamp=ts,
                sensor_ids=list(norm_scores.keys()),
                is_anomaly_station=is_anom_station,
                window_state_station=station_state,
                primary_anomaly_type=primary_type,
                missing_sensor_count=missing_count,
                valid_sensor_count=valid_count,
                normalized_sensor_scores=norm_scores,
                raw_sensor_values=raw_vals,
                split=split_name,
            )
        )

    return aligned_records


def compute_multivariate_fusion_scores(
    records: List[MultivariateTimestampRecord],
    strategy: str = "max",
    elevation_threshold: float = 1.5,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Compute station-level multivariate anomaly scores across aligned timestamp records.

    Strategies:
    - 'max': Max-sensor-context: strongest normalized anomaly signal across valid sensors.
    - 'mean': Mean-sensor-context: average normalized signal across valid sensors.
    - 'robust': Median + 0.5 * IQR dispersion.
    - 'agreement': Max signal scaled by cross-channel anomaly agreement ratio.
    - 'hybrid': 0.7 * Max signal + 0.3 * Mean of remaining sensors.

    Returns:
    --------
    scores : np.ndarray, shape (N,)
    y_true : np.ndarray, shape (N,)
    states : List[str]
    """
    scores = []
    y_true = []
    states = []

    for rec in records:
        y_true.append(rec.is_anomaly_station)
        states.append(rec.window_state_station)

        if rec.valid_sensor_count == 0:
            # Insufficient context
            scores.append(0.0)
            continue

        s_vals = np.array(list(rec.normalized_sensor_scores.values()), dtype=float)

        if strategy == "max":
            score = float(np.max(s_vals))
        elif strategy == "mean":
            score = float(np.mean(s_vals))
        elif strategy == "robust":
            med = float(np.median(s_vals))
            iqr = float(np.percentile(s_vals, 75) - np.percentile(s_vals, 25))
            score = med + 0.5 * iqr
        elif strategy == "agreement":
            max_s = float(np.max(s_vals))
            n_elevated = np.sum(s_vals > elevation_threshold)
            agreement_ratio = n_elevated / len(s_vals)
            score = max_s * (1.0 + 0.5 * agreement_ratio)
        elif strategy == "hybrid":
            if len(s_vals) > 1:
                sorted_vals = np.sort(s_vals)
                max_s = float(sorted_vals[-1])
                rest_mean = float(np.mean(sorted_vals[:-1]))
                score = 0.7 * max_s + 0.3 * rest_mean
            else:
                score = float(s_vals[0])
        else:
            raise ValueError(f"Unknown multivariate fusion strategy: {strategy}")

        scores.append(score)

    return np.array(scores, dtype=float), np.array(y_true, dtype=int), states
