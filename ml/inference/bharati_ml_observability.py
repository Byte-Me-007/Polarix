"""
Polarix Bharati ML Inference Observability and Audit Layer (SIH26060 - Person C).

Provides structured, deterministic diagnostic audit records and aggregate metrics for
Bharati ML inference operations, measuring processing latency with monotonic timers,
tracking rolling sequence buffer evolution, logging event types, and enabling offline auditing,
validation, and integration monitoring without altering ML inference decisions or model weights.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union

import numpy as np

from ml.inference.bharati_inference_contract import (
    DEFAULT_BHARATI_MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS,
    SUPPORTED_BHARATI_STATIONS,
    VALID_ANOMALY_TYPES,
    VALID_STATUSES,
    parse_iso_timestamp,
)

SUPPORTED_EVENT_TYPES: Set[str] = {
    "INFERENCE",
    "INSUFFICIENT_DATA",
    "MISSING_DATA",
    "DUPLICATE",
    "STALE",
    "INVALID_INPUT",
    "ERROR",
}


@dataclass(frozen=True)
class BharatiInferenceAuditRecord:
    """
    Structured diagnostic audit record for a single Bharati ML inference operation.
    """

    timestamp: str
    station_id: Optional[str]
    sensor_id: Optional[str]
    input_value_present: bool
    input_quality: Optional[str]
    input_accepted: bool
    event_type: str
    anomaly_status: Optional[str] = None
    anomaly_type: Optional[str] = None
    anomaly_score: Optional[float] = None
    threshold: Optional[float] = None
    model_version: Optional[str] = DEFAULT_BHARATI_MODEL_VERSION
    history_size_before: int = 0
    history_size_after: int = 0
    inference_eligible: bool = False
    state_changed: bool = False
    processing_time_ms: float = 0.0
    error_code: Optional[str] = None
    rejection_reason: Optional[str] = None

    def validate(self) -> None:
        """
        Validate data types and constraints on the audit record.
        """
        # 1. Validate event_type
        if self.event_type not in SUPPORTED_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type '{self.event_type}'. "
                f"Expected one of: {sorted(SUPPORTED_EVENT_TYPES)}"
            )

        # 2. Validate timestamp
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("Audit timestamp must be a non-empty string.")
        try:
            parse_iso_timestamp(self.timestamp)
        except Exception as e:
            raise ValueError(f"Audit timestamp is not a valid ISO-8601 string: {e}")

        # 3. Validate processing_time_ms
        if not isinstance(self.processing_time_ms, (int, float)):
            raise ValueError("processing_time_ms must be a numerical value.")
        if not math.isfinite(self.processing_time_ms) or self.processing_time_ms < 0.0:
            raise ValueError(
                f"processing_time_ms must be a finite, non-negative float. Got: {self.processing_time_ms}"
            )

        # 4. Validate anomaly_score
        if self.anomaly_score is not None:
            if not isinstance(self.anomaly_score, (int, float)) or not math.isfinite(self.anomaly_score):
                raise ValueError(
                    f"anomaly_score must be a finite float or None. Got: {self.anomaly_score}"
                )

        # 5. Validate threshold
        if self.threshold is not None:
            if not isinstance(self.threshold, (int, float)) or not math.isfinite(self.threshold):
                raise ValueError(
                    f"threshold must be a finite float or None. Got: {self.threshold}"
                )

        # 6. Validate history sizes
        if not isinstance(self.history_size_before, int) or self.history_size_before < 0:
            raise ValueError(f"history_size_before must be non-negative integer. Got: {self.history_size_before}")
        if not isinstance(self.history_size_after, int) or self.history_size_after < 0:
            raise ValueError(f"history_size_after must be non-negative integer. Got: {self.history_size_after}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert audit record into a deterministic, RFC 8259 JSON-serializable dictionary.
        """
        self.validate()
        return {
            "timestamp": self.timestamp,
            "station_id": self.station_id,
            "sensor_id": self.sensor_id,
            "input_value_present": self.input_value_present,
            "input_quality": self.input_quality,
            "input_accepted": self.input_accepted,
            "event_type": self.event_type,
            "anomaly_status": self.anomaly_status,
            "anomaly_type": self.anomaly_type,
            "anomaly_score": (
                round(float(self.anomaly_score), 6)
                if (self.anomaly_score is not None and math.isfinite(self.anomaly_score))
                else None
            ),
            "threshold": (
                round(float(self.threshold), 6)
                if (self.threshold is not None and math.isfinite(self.threshold))
                else None
            ),
            "model_version": self.model_version,
            "history_size_before": self.history_size_before,
            "history_size_after": self.history_size_after,
            "inference_eligible": self.inference_eligible,
            "state_changed": self.state_changed,
            "processing_time_ms": round(float(self.processing_time_ms), 4),
            "error_code": self.error_code,
            "rejection_reason": self.rejection_reason,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """
        Serialize audit record to a JSON string.
        """
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BharatiInferenceAuditRecord:
        """
        Construct a BharatiInferenceAuditRecord from a dictionary.
        """
        record = cls(
            timestamp=data["timestamp"],
            station_id=data.get("station_id"),
            sensor_id=data.get("sensor_id"),
            input_value_present=bool(data.get("input_value_present", False)),
            input_quality=data.get("input_quality"),
            input_accepted=bool(data.get("input_accepted", False)),
            event_type=data["event_type"],
            anomaly_status=data.get("anomaly_status"),
            anomaly_type=data.get("anomaly_type"),
            anomaly_score=data.get("anomaly_score"),
            threshold=data.get("threshold"),
            model_version=data.get("model_version", DEFAULT_BHARATI_MODEL_VERSION),
            history_size_before=int(data.get("history_size_before", 0)),
            history_size_after=int(data.get("history_size_after", 0)),
            inference_eligible=bool(data.get("inference_eligible", False)),
            state_changed=bool(data.get("state_changed", False)),
            processing_time_ms=float(data.get("processing_time_ms", 0.0)),
            error_code=data.get("error_code"),
            rejection_reason=data.get("rejection_reason"),
        )
        record.validate()
        return record

    @classmethod
    def from_json(cls, json_str: str) -> BharatiInferenceAuditRecord:
        """
        Construct a BharatiInferenceAuditRecord from a JSON string.
        """
        return cls.from_dict(json.loads(json_str))


def summarize_audit_records(records: List[BharatiInferenceAuditRecord]) -> Dict[str, Any]:
    """
    Summarize a collection of Bharati ML inference audit records.

    Parameters:
    -----------
    records : List[BharatiInferenceAuditRecord]
        List of audit records to aggregate.

    Returns:
    --------
    Dict[str, Any]:
        Aggregated summary including event counts, status counts, anomaly types, and latency percentiles.
    """
    if not records:
        return {
            "total_events": 0,
            "accepted_events": 0,
            "rejected_events": 0,
            "event_counts": {k: 0 for k in sorted(SUPPORTED_EVENT_TYPES)},
            "status_counts": {k: 0 for k in sorted(VALID_STATUSES)},
            "anomaly_type_counts": {k: 0 for k in sorted(VALID_ANOMALY_TYPES)},
            "latency_stats": {
                "count": 0,
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "min_latency_ms": 0.0,
            },
        }

    total_events = len(records)
    accepted_events = sum(1 for r in records if r.input_accepted)
    rejected_events = total_events - accepted_events

    event_counts = {k: 0 for k in sorted(SUPPORTED_EVENT_TYPES)}
    status_counts = {k: 0 for k in sorted(VALID_STATUSES)}
    anomaly_type_counts = {k: 0 for k in sorted(VALID_ANOMALY_TYPES)}

    latencies: List[float] = []

    for r in records:
        if r.event_type in event_counts:
            event_counts[r.event_type] += 1
        if r.anomaly_status and r.anomaly_status in status_counts:
            status_counts[r.anomaly_status] += 1
        if r.anomaly_type and r.anomaly_type in anomaly_type_counts:
            anomaly_type_counts[r.anomaly_type] += 1
        latencies.append(r.processing_time_ms)

    lat_arr = np.array(latencies, dtype=np.float64)
    avg_lat = float(np.mean(lat_arr)) if len(lat_arr) > 0 else 0.0
    p50_lat = float(np.percentile(lat_arr, 50)) if len(lat_arr) > 0 else 0.0
    p95_lat = float(np.percentile(lat_arr, 95)) if len(lat_arr) > 0 else 0.0
    max_lat = float(np.max(lat_arr)) if len(lat_arr) > 0 else 0.0
    min_lat = float(np.min(lat_arr)) if len(lat_arr) > 0 else 0.0

    return {
        "total_events": total_events,
        "accepted_events": accepted_events,
        "rejected_events": rejected_events,
        "event_counts": event_counts,
        "status_counts": status_counts,
        "anomaly_type_counts": anomaly_type_counts,
        "latency_stats": {
            "count": len(latencies),
            "avg_latency_ms": round(avg_lat, 4),
            "p50_latency_ms": round(p50_lat, 4),
            "p95_latency_ms": round(p95_lat, 4),
            "max_latency_ms": round(max_lat, 4),
            "min_latency_ms": round(min_lat, 4),
        },
    }
