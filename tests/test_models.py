from maitri.database import Base
from maitri.models import Device, SensorReading


def test_models_metadata():
    assert Device.__tablename__ == "devices"
    assert SensorReading.__tablename__ == "sensor_readings"
    assert "devices" in Base.metadata.tables
    assert "sensor_readings" in Base.metadata.tables
