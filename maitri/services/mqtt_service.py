import json
from typing import Any
from pydantic import ValidationError
from sqlalchemy.orm import Session

from maitri.config import settings
from maitri.models.telemetry import Telemetry
from maitri.schemas.sensor_reading import SensorReadingCreate
from maitri.schemas.telemetry import TelemetryCreate
from maitri.services.telemetry_service import create_telemetry


def build_station_telemetry_topic(station_code: str, prefix: str | None = None) -> str:
    """Build an MQTT topic for station telemetry. Format: {prefix}/{station_code}/telemetry"""
    pfx = (prefix or settings.mqtt_topic_prefix or "antarctic").strip("/")
    code = station_code.strip().upper()
    return f"{pfx}/{code}/telemetry"


def parse_station_telemetry_topic(topic: str, prefix: str | None = None) -> str | None:
    """Extract station code from a telemetry topic. E.g. 'antarctic/MTR/telemetry' -> 'MTR'"""
    pfx = (prefix or settings.mqtt_topic_prefix or "antarctic").strip("/")
    parts = topic.strip("/").split("/")
    if len(parts) == 3 and parts[0] == pfx and parts[2] == "telemetry":
        return parts[1].upper()
    return None


def parse_sensor_message(payload: str | bytes) -> SensorReadingCreate:
    """Parse and validate a legacy MQTT JSON payload into a SensorReadingCreate schema."""
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Payload must be a valid JSON object")

    try:
        return SensorReadingCreate(**data)
    except (ValidationError, TypeError) as exc:
        raise ValueError(f"Invalid sensor message format or missing fields: {exc}") from exc


def parse_telemetry_message(payload: str | bytes | dict, topic: str | None = None) -> TelemetryCreate:
    """
    Parse an MQTT telemetry payload (JSON string, bytes, or dict).
    If topic is provided, extracts station_code from topic if not present in payload.
    """
    if isinstance(payload, (str, bytes)):
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"Invalid JSON payload: {exc}") from exc
    elif isinstance(payload, dict):
        data = dict(payload)
    else:
        raise ValueError("Payload must be a valid JSON string, bytes, or dictionary")

    if not isinstance(data, dict):
        raise ValueError("Payload must be a valid JSON object")

    # If station_code is not in data, attempt extraction from topic
    if topic and not data.get("station_code") and not data.get("station_id"):
        extracted_station = parse_station_telemetry_topic(topic)
        if extracted_station:
            data["station_code"] = extracted_station

    # Default source to MQTT if not specified
    if not data.get("source"):
        data["source"] = "MQTT"

    try:
        return TelemetryCreate(**data)
    except (ValidationError, TypeError) as exc:
        raise ValueError(f"Invalid telemetry message format: {exc}") from exc


def ingest_mqtt_telemetry(
    db: Session,
    payload: str | bytes | dict,
    topic: str | None = None,
) -> Telemetry:
    """
    Ingests an MQTT telemetry message:
    - Parses payload and extracts station/sensor data
    - Validates station and sensor existence & association
    - Persists telemetry record to database
    - Triggers operational alerts on BAD/OFFLINE quality
    """
    telemetry_in = parse_telemetry_message(payload, topic=topic)
    return create_telemetry(db, telemetry_in)

