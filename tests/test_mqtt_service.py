import json
import pytest

from maitri.schemas.sensor_reading import SensorReadingCreate
from maitri.services.mqtt_service import parse_sensor_message


def test_parse_valid_sensor_message():
    payload = json.dumps(
        {
            "device_id": "device-001",
            "metric": "temperature",
            "value": 25.5,
            "unit": "celsius",
        }
    )
    result = parse_sensor_message(payload)
    assert isinstance(result, SensorReadingCreate)
    assert result.device_id == "device-001"
    assert result.metric == "temperature"
    assert result.value == 25.5
    assert result.unit == "celsius"


def test_parse_missing_required_field():
    # Missing 'metric'
    payload = json.dumps(
        {
            "device_id": "device-001",
            "value": 25.5,
        }
    )
    with pytest.raises(ValueError, match="Invalid sensor message format or missing fields"):
        parse_sensor_message(payload)


def test_parse_invalid_json():
    payload = "not a valid json {{"
    with pytest.raises(ValueError, match="Invalid JSON payload"):
        parse_sensor_message(payload)


def test_parse_numeric_value_as_float():
    payload = json.dumps(
        {
            "device_id": "device-002",
            "metric": "humidity",
            "value": 60,
        }
    )
    result = parse_sensor_message(payload)
    assert isinstance(result.value, float)
    assert result.value == 60.0
    assert result.unit is None
