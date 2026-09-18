from maitri.database import Base
from maitri.models import Alert, Device, Sensor, SensorReading, Station, Telemetry


def test_models_metadata():
    assert Device.__tablename__ == "devices"
    assert SensorReading.__tablename__ == "sensor_readings"
    assert Station.__tablename__ == "stations"
    assert Sensor.__tablename__ == "sensors"
    assert Telemetry.__tablename__ == "telemetry"
    assert Alert.__tablename__ == "alerts"
    assert "devices" in Base.metadata.tables
    assert "sensor_readings" in Base.metadata.tables
    assert "stations" in Base.metadata.tables
    assert "sensors" in Base.metadata.tables
    assert "telemetry" in Base.metadata.tables
    assert "alerts" in Base.metadata.tables

