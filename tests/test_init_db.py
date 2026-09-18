from sqlalchemy import create_engine, inspect

import maitri.models  # noqa: F401
from maitri.database import Base


def test_init_db():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)

    inspector = inspect(test_engine)
    table_names = inspector.get_table_names()

    assert "devices" in table_names
    assert "sensor_readings" in table_names
    assert "stations" in table_names
    assert "sensors" in table_names
    assert "telemetry" in table_names
    assert "alerts" in table_names

