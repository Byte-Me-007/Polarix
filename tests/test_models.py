from maitri.database import Base
from maitri.models import Device, Sensor, SensorReading, Station


def test_models_metadata():
    assert Device.__tablename__ == "devices"
    assert SensorReading.__tablename__ == "sensor_readings"
    assert Station.__tablename__ == "stations"
    assert Sensor.__tablename__ == "sensors"
    assert "devices" in Base.metadata.tables
    assert "sensor_readings" in Base.metadata.tables
    assert "stations" in Base.metadata.tables
    assert "sensors" in Base.metadata.tables
