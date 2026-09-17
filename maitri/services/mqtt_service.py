import json
from pydantic import ValidationError

from maitri.schemas.sensor_reading import SensorReadingCreate


def parse_sensor_message(payload: str) -> SensorReadingCreate:
    """Parse and validate an MQTT JSON payload into a SensorReadingCreate schema."""
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
