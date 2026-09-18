"""
Polarix Bharati ML Telemetry Inference Contract (SIH26060 - Person C).

Defines the typed data contracts between the Python sensor simulator / backend
and the Bharati machine learning anomaly-detection inference engine.

Design Principles:
- Zero dependency on FastAPI, Pydantic, or external web frameworks.
- Pure Python dataclasses with built-in JSON serialization and dictionary conversion.
- Preserves upstream telemetry metadata (station, sensor, timestamp, value, unit, quality, source).
- Strict station ('BRT') and sensor validation for Bharati station.
- Raw reconstruction error scoring (MSE) without arbitrary scaling or invented probability transforms.
- Clean handling of INSUFFICIENT_DATA and MISSING_DATA streaming states.
- Robust edge-case hardening (non-finite values, timestamp parse validation, quality enforcement).
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set, Union

import numpy as np

SUPPORTED_BHARATI_STATIONS: Set[str] = {"BRT"}

SUPPORTED_BHARATI_SENSORS: Set[str] = {
    "BRT_TEMP_001",
    "BRT_PRESS_001",
    "BRT_HUM_001",
    "BRT_VIB_001",
    "BRT_POWER_001",
}

VALID_STATUSES: Set[str] = {
    "NORMAL",
    "ANOMALY",
    "INSUFFICIENT_DATA",
    "MISSING_DATA",
}

VALID_QUALITIES: Set[str] = {
    "GOOD",
    "BAD",
    "MISSING",
    "UNCERTAIN",
}

DEFAULT_BHARATI_MODEL_VERSION: str = "lstm-ae-bharati-v1"


class UnsupportedStationError(ValueError):
    """Raised when telemetry is provided for an unsupported station."""
    pass


class UnsupportedSensorError(ValueError):
    """Raised when telemetry is provided for an unsupported sensor."""
    pass


class InvalidContractError(ValueError):
    """Raised when telemetry contract fails schema or type validation."""
    pass


class DuplicateTelemetryError(InvalidContractError):
    """Raised when duplicate telemetry with the same timestamp is received for a sensor."""
    pass


class StaleTelemetryError(InvalidContractError):
    """Raised when out-of-order telemetry with an older timestamp is received for a sensor."""
    pass


def parse_iso_timestamp(ts: str) -> datetime:
    """
    Parse an ISO-8601 formatted timestamp string into a UTC-normalized datetime object.

    Raises:
    -------
    InvalidContractError: If timestamp is not a valid parseable ISO string.
    """
    if not isinstance(ts, str) or not ts.strip():
        raise InvalidContractError("timestamp must be a non-empty string.")

    clean_ts = ts.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception as exc:
        raise InvalidContractError(f"Invalid timestamp format '{ts}': {exc}") from exc


@dataclass(frozen=True)
class BharatiTelemetryInput:
    """
    Standardized input contract for incoming Bharati telemetry observations.
    """

    station_id: str
    sensor_id: str
    timestamp: str
    value: Optional[float] = None
    unit: Optional[str] = None
    quality: str = "GOOD"
    source: Optional[str] = "SIMULATOR"

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate station, sensor, and metadata integrity."""
        if not self.station_id or not isinstance(self.station_id, str):
            raise InvalidContractError("station_id must be a non-empty string.")
        if self.station_id not in SUPPORTED_BHARATI_STATIONS:
            raise UnsupportedStationError(
                f"Unsupported station '{self.station_id}'. Supported stations: {sorted(SUPPORTED_BHARATI_STATIONS)}"
            )

        if not self.sensor_id or not isinstance(self.sensor_id, str):
            raise InvalidContractError("sensor_id must be a non-empty string.")
        if self.sensor_id not in SUPPORTED_BHARATI_SENSORS:
            raise UnsupportedSensorError(
                f"Unsupported sensor '{self.sensor_id}' for station '{self.station_id}'. Supported sensors: {sorted(SUPPORTED_BHARATI_SENSORS)}"
            )

        if not self.timestamp or not isinstance(self.timestamp, str):
            raise InvalidContractError("timestamp must be a non-empty string.")
        parse_iso_timestamp(self.timestamp)

        if self.quality not in VALID_QUALITIES:
            raise InvalidContractError(
                f"Invalid quality '{self.quality}'. Valid qualities: {sorted(VALID_QUALITIES)}"
            )

        if self.value is not None:
            try:
                converted_val = float(self.value)
                object.__setattr__(self, "value", converted_val)
            except (ValueError, TypeError) as exc:
                raise InvalidContractError(f"Invalid numeric value '{self.value}': {exc}") from exc

    def to_dict(self) -> Dict[str, Any]:
        """Convert input contract to dictionary."""
        return asdict(self)

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize input contract to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BharatiTelemetryInput:
        """Construct a BharatiTelemetryInput from a dictionary."""
        if not isinstance(data, dict):
            raise InvalidContractError(f"Expected dict, got {type(data).__name__}")
        return cls(
            station_id=str(data.get("station_id", "")),
            sensor_id=str(data.get("sensor_id", "")),
            timestamp=str(data.get("timestamp", "")),
            value=data.get("value"),
            unit=data.get("unit"),
            quality=str(data.get("quality", "GOOD")),
            source=data.get("source", "SIMULATOR"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> BharatiTelemetryInput:
        """Construct a BharatiTelemetryInput from a JSON string."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise InvalidContractError(f"Invalid JSON string: {exc}") from exc
        return cls.from_dict(data)


VALID_ANOMALY_TYPES: Set[str] = {
    "NORMAL",
    "SPIKE",
    "DRIFT",
    "STUCK_VALUE",
    "UNKNOWN",
}


@dataclass(frozen=True)
class BharatiTelemetryOutput:
    """
    Standardized output contract returned by the Bharati ML inference engine.
    """

    station_id: str
    sensor_id: str
    timestamp: str
    value: Optional[float]
    unit: Optional[str]
    quality: str
    source: Optional[str]
    anomaly_score: Optional[float]
    anomaly_status: str
    anomaly_type: Optional[str] = None
    model_version: str = DEFAULT_BHARATI_MODEL_VERSION

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate inference output contract fields."""
        if self.station_id not in SUPPORTED_BHARATI_STATIONS:
            raise UnsupportedStationError(f"Unsupported station '{self.station_id}'.")
        if self.sensor_id not in SUPPORTED_BHARATI_SENSORS:
            raise UnsupportedSensorError(f"Unsupported sensor '{self.sensor_id}'.")
        if self.anomaly_status not in VALID_STATUSES:
            raise InvalidContractError(
                f"Invalid anomaly_status '{self.anomaly_status}'. Valid statuses: {sorted(VALID_STATUSES)}"
            )
        if self.anomaly_status in {"INSUFFICIENT_DATA", "MISSING_DATA"}:
            if self.anomaly_score is not None:
                raise InvalidContractError(
                    f"anomaly_score must be None when status is '{self.anomaly_status}'."
                )
            if self.anomaly_type is not None:
                raise InvalidContractError(
                    f"anomaly_type must be None when status is '{self.anomaly_status}'."
                )
        if self.anomaly_status in {"NORMAL", "ANOMALY"}:
            if self.anomaly_score is None:
                raise InvalidContractError(
                    f"anomaly_score cannot be None when status is '{self.anomaly_status}'."
                )
            if not np.isfinite(self.anomaly_score):
                raise InvalidContractError("anomaly_score must be a finite float.")

        if self.anomaly_type is not None and self.anomaly_type not in VALID_ANOMALY_TYPES:
            raise InvalidContractError(
                f"Invalid anomaly_type '{self.anomaly_type}'. Valid types: {sorted(VALID_ANOMALY_TYPES)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert output contract to dictionary, sanitizing non-finite values to None for clean JSON compliance."""
        d = asdict(self)
        if d.get("value") is not None and isinstance(d["value"], (int, float)) and not math.isfinite(d["value"]):
            d["value"] = None
        if d.get("anomaly_score") is not None and isinstance(d["anomaly_score"], (int, float)) and not math.isfinite(d["anomaly_score"]):
            d["anomaly_score"] = None
        return d

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize output contract to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def __getitem__(self, key: str) -> Any:
        """Dict-like access for backwards compatibility with dictionary interfaces."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        """Dict-like membership testing."""
        return hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like get method."""
        return getattr(self, key, default)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BharatiTelemetryOutput:
        """Construct a BharatiTelemetryOutput from a dictionary."""
        if not isinstance(data, dict):
            raise InvalidContractError(f"Expected dict, got {type(data).__name__}")
        return cls(
            station_id=str(data.get("station_id", "")),
            sensor_id=str(data.get("sensor_id", "")),
            timestamp=str(data.get("timestamp", "")),
            value=data.get("value"),
            unit=data.get("unit"),
            quality=str(data.get("quality", "GOOD")),
            source=data.get("source"),
            anomaly_score=data.get("anomaly_score"),
            anomaly_status=str(data.get("anomaly_status", "")),
            anomaly_type=data.get("anomaly_type"),
            model_version=str(data.get("model_version", DEFAULT_BHARATI_MODEL_VERSION)),
        )

    @classmethod
    def from_json(cls, json_str: str) -> BharatiTelemetryOutput:
        """Construct a BharatiTelemetryOutput from a JSON string."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise InvalidContractError(f"Invalid JSON string: {exc}") from exc
        return cls.from_dict(data)
