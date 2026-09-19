import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base
from maitri.schemas.device import DeviceCreate
from maitri.schemas.sensor_reading import SensorReadingCreate
from maitri.services import (
    create_device,
    get_device_by_device_id,
    list_devices,
    create_sensor_reading,
    list_sensor_readings,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_device_service(db_session):
    device_data_1 = DeviceCreate(
        device_id="DEV-001",
        name="Main Temperature Sensor",
        location="Lab Room 1",
        status="active",
    )
    device_data_2 = DeviceCreate(
        device_id="DEV-002",
        name="Pressure Sensor",
        location="Lab Room 2",
        status="inactive",
    )

    dev1 = create_device(db_session, device_data_1)
    assert dev1.id is not None
    assert dev1.device_id == "DEV-001"
    assert dev1.status == "active"

    dev2 = create_device(db_session, device_data_2)
    assert dev2.id is not None
    assert dev2.device_id == "DEV-002"

    devices = list_devices(db_session)
    assert len(devices) == 2

    found = get_device_by_device_id(db_session, "DEV-001")
    assert found is not None
    assert found.name == "Main Temperature Sensor"

    not_found = get_device_by_device_id(db_session, "NON-EXISTENT")
    assert not_found is None


def test_sensor_service(db_session):
    reading_1 = SensorReadingCreate(
        device_id="DEV-001",
        metric="temperature",
        value=21.5,
        unit="C",
    )
    reading_2 = SensorReadingCreate(
        device_id="DEV-001",
        metric="humidity",
        value=55.0,
        unit="%",
    )
    reading_3 = SensorReadingCreate(
        device_id="DEV-002",
        metric="pressure",
        value=1013.25,
        unit="hPa",
    )

    create_sensor_reading(db_session, reading_1)
    create_sensor_reading(db_session, reading_2)
    create_sensor_reading(db_session, reading_3)

    all_readings = list_sensor_readings(db_session)
    assert len(all_readings) == 3

    dev1_readings = list_sensor_readings(db_session, device_id="DEV-001")
    assert len(dev1_readings) == 2
    assert all(r.device_id == "DEV-001" for r in dev1_readings)

    dev2_readings = list_sensor_readings(db_session, device_id="DEV-002")
    assert len(dev2_readings) == 1
    assert dev2_readings[0].metric == "pressure"
