import json
from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base
from maitri.models.alert import Alert
from maitri.models.telemetry import Telemetry
from maitri.schemas.sensor_reading import SensorReadingCreate
from maitri.schemas.telemetry import TelemetryCreate
from maitri.services.mqtt_service import (
    build_station_telemetry_topic,
    ingest_mqtt_telemetry,
    parse_sensor_message,
    parse_station_telemetry_topic,
    parse_telemetry_message,
)
from maitri.services.station_service import seed_default_stations
from maitri.simulator import (
    generate_telemetry_batch,
    publish_simulated_telemetry,
    serialize_telemetry_payload,
)


@pytest.fixture
def db_session():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    db = TestingSessionLocal()
    seed_default_stations(db)
    try:
        yield db
    finally:
        db.close()


# 1. Legacy Sensor Message Parsing Tests
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


# 2. Topic Construction and Parsing Tests
def test_mqtt_topic_construction():
    topic_mtr = build_station_telemetry_topic("MTR")
    assert topic_mtr == "antarctic/MTR/telemetry"

    topic_bhr = build_station_telemetry_topic("bhr")
    assert topic_bhr == "antarctic/BHR/telemetry"

    custom_topic = build_station_telemetry_topic("MTR", prefix="polar_grid")
    assert custom_topic == "polar_grid/MTR/telemetry"


def test_mqtt_topic_parsing():
    assert parse_station_telemetry_topic("antarctic/MTR/telemetry") == "MTR"
    assert parse_station_telemetry_topic("antarctic/bhr/telemetry") == "BHR"
    assert parse_station_telemetry_topic("custom/MTR/telemetry", prefix="custom") == "MTR"
    assert parse_station_telemetry_topic("antarctic/MTR/status") is None
    assert parse_station_telemetry_topic("invalid/topic") is None


# 3. Simulator MQTT Payload and Publishing Tests
def test_simulator_mqtt_payload_structure_and_publishing():
    mock_client = MagicMock()
    batch = publish_simulated_telemetry(
        station_code="MTR",
        scenario="NORMAL_DAY",
        step=1,
        client=mock_client,
    )
    assert len(batch) == 5
    assert mock_client.publish.call_count == 5

    for call_args in mock_client.publish.call_args_list:
        topic, payload_str = call_args[0]
        assert topic == "antarctic/MTR/telemetry"
        data = json.loads(payload_str)
        assert data["station_code"] == "MTR"
        assert data["source"] == "SIMULATOR"
        assert "sensor_code" in data
        assert "value" in data
        assert "quality" in data
        assert "timestamp" in data


def test_serialize_telemetry_payload():
    record = {
        "station_code": "MTR",
        "sensor_code": "MTR-ENV-TMP-01",
        "value": -19.2,
        "quality": "GOOD",
    }
    serialized = serialize_telemetry_payload(record)
    assert isinstance(serialized, str)
    parsed = json.loads(serialized)
    assert parsed["value"] == -19.2


# 4. Backend MQTT Telemetry Parsing Tests
def test_backend_mqtt_message_parsing_json_string():
    payload = json.dumps(
        {
            "station_code": "MTR",
            "sensor_code": "MTR-ENV-TMP-01",
            "value": -21.4,
            "quality": "GOOD",
        }
    )
    parsed = parse_telemetry_message(payload)
    assert isinstance(parsed, TelemetryCreate)
    assert parsed.station_code == "MTR"
    assert parsed.sensor_code == "MTR-ENV-TMP-01"
    assert parsed.value == -21.4
    assert parsed.source == "MQTT"


def test_backend_mqtt_message_parsing_from_topic_extraction():
    payload = json.dumps(
        {
            "sensor_code": "MTR-ENV-TMP-01",
            "value": -21.4,
            "quality": "GOOD",
        }
    )
    parsed = parse_telemetry_message(payload, topic="antarctic/MTR/telemetry")
    assert parsed.station_code == "MTR"
    assert parsed.sensor_code == "MTR-ENV-TMP-01"


def test_backend_mqtt_message_parsing_bytes_and_dict():
    raw_dict = {
        "station_code": "BHR",
        "sensor_code": "BHR-ENV-TMP-01",
        "value": -14.2,
    }
    parsed_from_dict = parse_telemetry_message(raw_dict)
    assert parsed_from_dict.station_code == "BHR"
    assert parsed_from_dict.value == -14.2

    bytes_payload = json.dumps(raw_dict).encode("utf-8")
    parsed_from_bytes = parse_telemetry_message(bytes_payload)
    assert parsed_from_bytes.station_code == "BHR"


def test_backend_mqtt_message_parsing_invalid():
    with pytest.raises(ValueError, match="Invalid JSON payload"):
        parse_telemetry_message("invalid json")

    with pytest.raises(ValueError, match="Payload must be a valid JSON object"):
        parse_telemetry_message(json.dumps(["not", "a", "dict"]))

    with pytest.raises(ValueError, match="Payload must be a valid JSON string"):
        parse_telemetry_message(12345)


# 5. Valid MQTT Telemetry Ingestion Test
def test_valid_mqtt_telemetry_ingestion(db_session):
    payload = json.dumps(
        {
            "station_code": "MTR",
            "sensor_code": "MTR-ENV-TMP-01",
            "value": -19.5,
            "quality": "GOOD",
            "anomaly_score": 0.03,
        }
    )
    record = ingest_mqtt_telemetry(db_session, payload)
    assert isinstance(record, Telemetry)
    assert record.id is not None
    assert record.value == -19.5
    assert record.quality == "GOOD"
    assert record.source == "MQTT"
    assert record.unit == "°C"

    # Query directly from DB
    persisted = db_session.query(Telemetry).filter(Telemetry.id == record.id).first()
    assert persisted is not None
    assert persisted.value == -19.5


# 6. Invalid Station Handling Test
def test_invalid_station_handling(db_session):
    payload = json.dumps(
        {
            "station_code": "NON_EXISTENT_STATION",
            "sensor_code": "MTR-ENV-TMP-01",
            "value": -10.0,
        }
    )
    with pytest.raises(ValueError, match="Station not found"):
        ingest_mqtt_telemetry(db_session, payload)


# 7. Invalid Sensor Handling Test
def test_invalid_sensor_handling(db_session):
    # Non-existent sensor
    payload_bad_sensor = json.dumps(
        {
            "station_code": "MTR",
            "sensor_code": "UNKNOWN-SENSOR-99",
            "value": 10.0,
        }
    )
    with pytest.raises(ValueError, match="Sensor not found"):
        ingest_mqtt_telemetry(db_session, payload_bad_sensor)

    # Sensor belongs to BHR, not MTR
    payload_mismatch = json.dumps(
        {
            "station_code": "MTR",
            "sensor_code": "BHR-ENV-TMP-01",
            "value": 10.0,
        }
    )
    with pytest.raises(ValueError, match="does not belong to station"):
        ingest_mqtt_telemetry(db_session, payload_mismatch)


# 8. BAD Quality Alert Trigger Test
def test_bad_quality_alert_trigger(db_session):
    payload = json.dumps(
        {
            "station_code": "MTR",
            "sensor_code": "MTR-ENG-GEN-01",
            "value": 12.0,
            "quality": "BAD",
            "anomaly_score": 0.95,
        }
    )
    record = ingest_mqtt_telemetry(db_session, payload)
    assert record.quality == "BAD"

    alert = (
        db_session.query(Alert)
        .filter(
            Alert.station_id == record.station_id,
            Alert.sensor_id == record.sensor_id,
            Alert.alert_type == "SENSOR_FAULT",
        )
        .first()
    )
    assert alert is not None
    assert alert.severity == "HIGH"
    assert "BAD quality" in alert.message


# 9. OFFLINE Quality Critical Alert Trigger Test
def test_offline_quality_critical_alert_trigger(db_session):
    payload = json.dumps(
        {
            "station_code": "BHR",
            "sensor_code": "BHR-ENV-TMP-01",
            "value": 0.0,
            "quality": "OFFLINE",
            "anomaly_score": 1.0,
        }
    )
    record = ingest_mqtt_telemetry(
        db_session, payload, topic="antarctic/BHR/telemetry"
    )
    assert record.quality == "OFFLINE"

    alert = (
        db_session.query(Alert)
        .filter(
            Alert.station_id == record.station_id,
            Alert.sensor_id == record.sensor_id,
            Alert.alert_type == "SENSOR_OFFLINE",
        )
        .first()
    )
    assert alert is not None
    assert alert.severity == "CRITICAL"
    assert "OFFLINE" in alert.message

