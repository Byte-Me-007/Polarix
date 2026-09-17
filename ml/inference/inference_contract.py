"""
Polarix ML Telemetry Inference Contract (SIH26060 - Person C).

Defines the typed data contracts between the Python sensor simulator / backend
and the machine learning anomaly-detection inference engine.

Design Principles:
- Zero dependency on FastAPI, Pydantic, or external web frameworks.
- Pure Python dataclasses with built-in JSON serialization and dictionary conversion.
- Preserves upstream telemetry metadata (station, sensor, timestamp, value, unit, quality, source).
- Strict station ('MTR') and sensor validation for Maitri station.
- Raw reconstruction error scoring (MSE) without arbitrary scaling or invented probability transforms.
- Clean handling of INSUFFICIENT_DATA and MISSING_DATA streaming states.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Set, Union

SUPPORTED_STATIONS: Set[str] = {"MTR"}

SUPPORTED_SENSORS: Set[str] = {
    "TEMP_001",
    "PRESS_001",
    "HUM_001",
    "VIB_001",
    "POWER_001",
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

DEFAULT_MODEL_VERSION: str = "lstm-ae-v1"


class UnsupportedStationError(ValueError):
    """Raised when telemetry is provided for an unsupported station."""
    pass


class UnsupportedSensorError(ValueError):
    """Raised when telemetry is provided for an unsupported sensor."""
    pass


class InvalidContractError(ValueError):
    """Raised when telemetry contract fails schema or type validation."""
    pass


@dataclass(frozen=True)
class TelemetryInput:
    """
    Standardized input contract for incoming telemetry observations.
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
        if not self.station_id:
            raise InvalidContractError("station_id must be a non-empty string.")
        if self.station_id not in SUPPORTED_STATIONS:
            raise UnsupportedStationError(
                f"Unsupported station '{self.station_id}'. Currently supported stations: {sorted(SUPPORTED_STATIONS)}"
            )

        if not self.sensor_id:
            raise InvalidContractError("sensor_id must be a non-empty string.")
        if self.sensor_id not in SUPPORTED_SENSORS:
            raise UnsupportedSensorError(
                f"Unsupported sensor '{self.sensor_id}' for station '{self.station_id}'. Supported sensors: {sorted(SUPPORTED_SENSORS)}"
            )

        if not self.timestamp:
            raise InvalidContractError("timestamp must be a non-empty string.")

        if self.value is not None:
            try:
                object.__setattr__(self, "value", float(self.value))
            except (ValueError, TypeError) as exc:
                raise InvalidContractError(f"Invalid numeric value '{self.value}': {exc}") from exc

    def to_dict(self) -> Dict[str, Any]:
        """Convert input contract to dictionary."""
        return asdict(self)

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize input contract to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TelemetryInput:
        """Construct a TelemetryInput from a dictionary."""
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
    def from_json(cls, json_str: str) -> TelemetryInput:
        """Construct a TelemetryInput from a JSON string."""
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
class TelemetryInferenceOutput:
    """
    Standardized output contract returned by the ML inference engine.
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
    model_version: str = DEFAULT_MODEL_VERSION

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate inference output contract fields."""
        if self.station_id not in SUPPORTED_STATIONS:
            raise UnsupportedStationError(f"Unsupported station '{self.station_id}'.")
        if self.sensor_id not in SUPPORTED_SENSORS:
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
        if self.anomaly_status in {"NORMAL", "ANOMALY"} and self.anomaly_score is None:
            raise InvalidContractError(
                f"anomaly_score cannot be None when status is '{self.anomaly_status}'."
            )
        if self.anomaly_type is not None and self.anomaly_type not in VALID_ANOMALY_TYPES:
            raise InvalidContractError(
                f"Invalid anomaly_type '{self.anomaly_type}'. Valid types: {sorted(VALID_ANOMALY_TYPES)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert output contract to dictionary."""
        return asdict(self)

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
    def from_dict(cls, data: Dict[str, Any]) -> TelemetryInferenceOutput:
        """Construct a TelemetryInferenceOutput from a dictionary."""
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
            model_version=str(data.get("model_version", DEFAULT_MODEL_VERSION)),
        )

    @classmethod
    def from_json(cls, json_str: str) -> TelemetryInferenceOutput:
        """Construct a TelemetryInferenceOutput from a JSON string."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise InvalidContractError(f"Invalid JSON string: {exc}") from exc
        return cls.from_dict(data)
