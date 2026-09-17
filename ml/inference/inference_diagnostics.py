"""
Maitri ML Inference Observability and Structured Audit Diagnostics.
Polarix SIH26060 - Person C.

Provides structured, deterministic diagnostic records for each ML inference operation,
measuring processing latency, tracking sequence buffer lengths, logging operation
statuses, and enabling offline auditing, validation, and integration monitoring
without altering ML inference decisions or model weights.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from ml.inference.inference_contract import parse_iso_timestamp

DIAGNOSTIC_STATUSES: Set[str] = {
    "SUCCESS",
    "INSUFFICIENT_DATA",
    "MISSING_DATA",
    "REJECTED_DUPLICATE",
    "REJECTED_STALE",
    "REJECTED_INVALID",
    "ERROR",
}


@dataclass(frozen=True)
class InferenceDiagnosticRecord:
    """
    Structured diagnostic audit record for a single ML inference operation.
    """

    timestamp: str
    station_id: Optional[str]
    sensor_id: Optional[str]
    inference_status: str
    anomaly_status: Optional[str] = None
    anomaly_type: Optional[str] = None
    anomaly_score: Optional[float] = None
    threshold: Optional[float] = None
    model_version: Optional[str] = None
    buffer_length: Optional[int] = None
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None

    def validate(self) -> None:
        """
        Validate data types and constraints on the diagnostic record.
        """
        # 1. Validate inference_status
        if self.inference_status not in DIAGNOSTIC_STATUSES:
            raise ValueError(
                f"Invalid inference_status '{self.inference_status}'. "
                f"Expected one of: {sorted(DIAGNOSTIC_STATUSES)}"
            )

        # 2. Validate timestamp
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("Diagnostic timestamp must be a non-empty ISO-8601 string.")
        try:
            parse_iso_timestamp(self.timestamp)
        except Exception as e:
            raise ValueError(f"Diagnostic timestamp is not a valid ISO-8601 string: {e}")

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

        # 6. Validate buffer_length
        if self.buffer_length is not None:
            if not isinstance(self.buffer_length, int) or self.buffer_length < 0:
                raise ValueError(
                    f"buffer_length must be a non-negative integer or None. Got: {self.buffer_length}"
                )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert diagnostic record into a deterministic, JSON-serializable dictionary.
        """
        self.validate()
        return {
            "timestamp": self.timestamp,
            "station_id": self.station_id,
            "sensor_id": self.sensor_id,
            "inference_status": self.inference_status,
            "anomaly_status": self.anomaly_status,
            "anomaly_type": self.anomaly_type,
            "anomaly_score": round(float(self.anomaly_score), 6) if self.anomaly_score is not None else None,
            "threshold": round(float(self.threshold), 6) if self.threshold is not None else None,
            "model_version": self.model_version,
            "buffer_length": self.buffer_length,
            "processing_time_ms": round(float(self.processing_time_ms), 4),
            "error_message": self.error_message,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """
        Serialize diagnostic record to a JSON string.
        """
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InferenceDiagnosticRecord:
        """
        Construct an InferenceDiagnosticRecord from a dictionary.
        """
        record = cls(
            timestamp=data["timestamp"],
            station_id=data.get("station_id"),
            sensor_id=data.get("sensor_id"),
            inference_status=data["inference_status"],
            anomaly_status=data.get("anomaly_status"),
            anomaly_type=data.get("anomaly_type"),
            anomaly_score=data.get("anomaly_score"),
            threshold=data.get("threshold"),
            model_version=data.get("model_version"),
            buffer_length=data.get("buffer_length"),
            processing_time_ms=data.get("processing_time_ms", 0.0),
            error_message=data.get("error_message"),
        )
        record.validate()
        return record

    @classmethod
    def from_json(cls, json_str: str) -> InferenceDiagnosticRecord:
        """
        Construct an InferenceDiagnosticRecord from a JSON string.
        """
        return cls.from_dict(json.loads(json_str))
