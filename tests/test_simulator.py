import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app
from maitri.schemas.telemetry import TelemetryCreate
from maitri.services.station_service import seed_default_stations
from maitri.simulator import (
    SUPPORTED_SCENARIOS,
    generate_telemetry_batch,
    get_supported_scenarios,
)


@pytest.fixture
def client():
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
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_supported_scenarios():
    scenarios = get_supported_scenarios()
    expected = [
        "NORMAL_DAY",
        "STORM",
        "POWER_CRISIS",
        "SENSOR_FAILURE",
        "SATELLITE_OUTAGE",
        "RECOVERY",
    ]
    for s in expected:
        assert s in scenarios


def test_valid_station_generation_maitri():
    batch = generate_telemetry_batch("MTR", scenario="NORMAL_DAY")
    assert isinstance(batch, list)
    assert len(batch) == 5
    for item in batch:
        assert item["station_code"] == "MTR"
        assert item["source"] == "SIMULATOR"
        assert item["quality"] == "GOOD"
        # Validate schema compatibility
        validated = TelemetryCreate(**item)
        assert validated.station_code == "MTR"


def test_valid_station_generation_bharati():
    batch = generate_telemetry_batch("BHR", scenario="NORMAL_DAY")
    assert isinstance(batch, list)
    assert len(batch) == 4
    for item in batch:
        assert item["station_code"] == "BHR"
        assert item["source"] == "SIMULATOR"
        validated = TelemetryCreate(**item)
        assert validated.station_code == "BHR"


def test_invalid_station_handling():
    with pytest.raises(ValueError) as exc_info:
        generate_telemetry_batch("INVALID_STATION")
    assert "invalid station code" in str(exc_info.value).lower()


def test_invalid_scenario_handling():
    with pytest.raises(ValueError) as exc_info:
        generate_telemetry_batch("MTR", scenario="ALIEN_INVASION")
    assert "unknown scenario" in str(exc_info.value).lower()


def test_payload_compatibility_with_telemetry_endpoint(client):
    batch = generate_telemetry_batch("MTR", scenario="NORMAL_DAY")
    for payload in batch:
        # Convert timestamp to ISO format string for JSON post
        payload_copy = dict(payload)
        payload_copy["timestamp"] = payload_copy["timestamp"].isoformat()
        response = client.post("/telemetry/", json=payload_copy)
        assert response.status_code == 201
        data = response.json()
        assert data["station_id"] is not None
        assert data["sensor_id"] is not None


def test_storm_changes_environmental_readings():
    normal_batch = generate_telemetry_batch("MTR", scenario="NORMAL_DAY", step=0)
    storm_batch = generate_telemetry_batch("MTR", scenario="STORM", step=0)

    normal_wind = next(s for s in normal_batch if "WND" in s["sensor_code"])
    storm_wind = next(s for s in storm_batch if "WND" in s["sensor_code"])
    assert storm_wind["value"] > normal_wind["value"] + 30.0  # wind spikes

    normal_temp = next(s for s in normal_batch if "TMP" in s["sensor_code"])
    storm_temp = next(s for s in storm_batch if "TMP" in s["sensor_code"])
    assert storm_temp["value"] < normal_temp["value"] - 15.0  # temp plunges


def test_power_crisis_changes_energy_readings():
    normal_batch = generate_telemetry_batch("MTR", scenario="NORMAL_DAY")
    crisis_batch = generate_telemetry_batch("MTR", scenario="POWER_CRISIS")

    normal_gen = next(s for s in normal_batch if "GEN" in s["sensor_code"])
    crisis_gen = next(s for s in crisis_batch if "GEN" in s["sensor_code"])
    assert crisis_gen["value"] < normal_gen["value"] * 0.5  # generator output collapses
    assert crisis_gen["quality"] == "BAD"


def test_sensor_failure_produces_bad_quality():
    failure_batch = generate_telemetry_batch("MTR", scenario="SENSOR_FAILURE")
    failed_sensor = next(s for s in failure_batch if "TMP" in s["sensor_code"])
    assert failed_sensor["quality"] == "BAD"
    assert failed_sensor["value"] == -999.0
    assert failed_sensor["anomaly_score"] >= 0.95


def test_satellite_outage_produces_unsynced_telemetry():
    outage_batch = generate_telemetry_batch("BHR", scenario="SATELLITE_OUTAGE")
    for item in outage_batch:
        assert item["synced"] is False


def test_recovery_produces_normalizing_readings():
    recovery_start = generate_telemetry_batch("MTR", scenario="RECOVERY", step=0)
    recovery_later = generate_telemetry_batch("MTR", scenario="RECOVERY", step=15)

    temp_start = next(s for s in recovery_start if "TMP" in s["sensor_code"])
    temp_later = next(s for s in recovery_later if "TMP" in s["sensor_code"])

    # As step increases, recovery decays toward nominal base (-20.0 °C)
    assert abs(temp_later["value"] - (-20.0)) < abs(temp_start["value"] - (-20.0))
