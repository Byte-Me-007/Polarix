from datetime import datetime, timezone

from maitri.schemas import (
    DeviceCreate,
    DeviceResponse,
    SensorReadingCreate,
    SensorReadingResponse,
)


def test_device_schemas():
    device_data = DeviceCreate(
        device_id="DEV-001",
        name="Temperature Sensor 1",
        location="Living Room",
        status="active",
    )
    assert device_data.device_id == "DEV-001"
    assert device_data.name == "Temperature Sensor 1"
    assert device_data.location == "Living Room"
    assert device_data.status == "active"

    now = datetime.now(timezone.utc)
    device_resp = DeviceResponse(
        id=1,
        device_id="DEV-001",
        name="Temperature Sensor 1",
        location="Living Room",
        status="active",
        created_at=now,
    )
    assert device_resp.id == 1
    assert device_resp.created_at == now


def test_sensor_reading_schemas():
    reading_data = SensorReadingCreate(
        device_id="DEV-001",
        metric="temperature",
        value=24.5,
        unit="C",
    )
    assert reading_data.device_id == "DEV-001"
    assert reading_data.metric == "temperature"
    assert reading_data.value == 24.5
    assert reading_data.unit == "C"

    now = datetime.now(timezone.utc)
    reading_resp = SensorReadingResponse(
        id=10,
        device_id="DEV-001",
        metric="temperature",
        value=24.5,
        unit="C",
        recorded_at=now,
    )
    assert reading_resp.id == 10
    assert reading_resp.recorded_at == now
