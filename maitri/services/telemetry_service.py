from datetime import datetime, timezone
from sqlalchemy import desc
from sqlalchemy.orm import Session

from maitri.models.sensor import Sensor
from maitri.models.station import Station
from maitri.models.telemetry import Telemetry
from maitri.schemas.alert import AlertCreate
from maitri.schemas.telemetry import TelemetryCreate
from maitri.services.alert_service import create_alert
from maitri.services.station_service import get_station_by_id_or_code

VALID_QUALITIES = {"GOOD", "WARNING", "BAD", "UNKNOWN", "OFFLINE"}
VALID_SOURCES = {"SIMULATOR", "MQTT", "API"}


def create_telemetry(db: Session, telemetry_in: TelemetryCreate) -> Telemetry:
    # 1. Validate station
    station = None
    if telemetry_in.station_id is not None:
        station = db.query(Station).filter(Station.id == telemetry_in.station_id).first()
    elif telemetry_in.station_code is not None:
        station = get_station_by_id_or_code(db, telemetry_in.station_code)

    if not station:
        raise ValueError("Station not found")

    # 2. Validate sensor
    sensor = None
    if telemetry_in.sensor_id is not None:
        sensor = db.query(Sensor).filter(Sensor.id == telemetry_in.sensor_id).first()
    elif telemetry_in.sensor_code is not None:
        sensor = db.query(Sensor).filter(Sensor.sensor_code == telemetry_in.sensor_code).first()

    if not sensor:
        raise ValueError("Sensor not found")

    # 3. Validate sensor belongs to station
    if sensor.station_id != station.id:
        raise ValueError(
            f"Sensor '{sensor.sensor_code}' does not belong to station '{station.station_code}'"
        )

    quality = telemetry_in.quality.upper() if telemetry_in.quality else "GOOD"
    if quality not in VALID_QUALITIES:
        quality = "UNKNOWN"

    source = telemetry_in.source.upper() if telemetry_in.source else "API"
    if source not in VALID_SOURCES:
        source = "API"

    unit = telemetry_in.unit if telemetry_in.unit is not None else sensor.unit
    ts = (
        telemetry_in.timestamp
        if telemetry_in.timestamp is not None
        else datetime.now(timezone.utc)
    )

    telemetry_record = Telemetry(
        station_id=station.id,
        sensor_id=sensor.id,
        timestamp=ts,
        value=telemetry_in.value,
        unit=unit,
        quality=quality,
        source=source,
        anomaly_score=telemetry_in.anomaly_score,
        synced=telemetry_in.synced,
    )
    db.add(telemetry_record)
    db.commit()
    db.refresh(telemetry_record)

    # Optional simple alert creation for BAD or OFFLINE telemetry
    if quality == "BAD":
        create_alert(
            db,
            AlertCreate(
                station_id=station.id,
                sensor_id=sensor.id,
                severity="HIGH",
                alert_type="SENSOR_FAULT",
                title=f"Sensor Fault: {sensor.sensor_code}",
                message=f"Sensor '{sensor.sensor_code}' at station '{station.station_code}' reported BAD quality.",
                anomaly_score=telemetry_in.anomaly_score,
            ),
        )
    elif quality == "OFFLINE":
        create_alert(
            db,
            AlertCreate(
                station_id=station.id,
                sensor_id=sensor.id,
                severity="CRITICAL",
                alert_type="SENSOR_OFFLINE",
                title=f"Sensor Offline: {sensor.sensor_code}",
                message=f"Sensor '{sensor.sensor_code}' at station '{station.station_code}' is OFFLINE.",
                anomaly_score=telemetry_in.anomaly_score,
            ),
        )

    return telemetry_record


def get_telemetry_by_station(
    db: Session, station_id_or_code: str | int, limit: int = 100
) -> list[Telemetry]:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        return []
    return (
        db.query(Telemetry)
        .filter(Telemetry.station_id == station.id)
        .order_by(desc(Telemetry.timestamp), desc(Telemetry.id))
        .limit(limit)
        .all()
    )


def get_latest_telemetry_by_station(
    db: Session, station_id_or_code: str | int
) -> list[Telemetry]:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        return []

    sensors = db.query(Sensor).filter(Sensor.station_id == station.id).all()
    latest_readings = []
    for sensor in sensors:
        latest = (
            db.query(Telemetry)
            .filter(
                Telemetry.station_id == station.id,
                Telemetry.sensor_id == sensor.id,
            )
            .order_by(desc(Telemetry.timestamp), desc(Telemetry.id))
            .first()
        )
        if latest:
            latest_readings.append(latest)
    return latest_readings
