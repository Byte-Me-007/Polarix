from datetime import datetime, timezone
from sqlalchemy import desc
from sqlalchemy.orm import Session

from maitri.models.alert import Alert
from maitri.models.sensor import Sensor
from maitri.models.station import Station
from maitri.schemas.alert import AlertCreate
from maitri.services.station_service import get_station_by_id_or_code

VALID_SEVERITIES = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_STATUSES = {"ACTIVE", "ACKNOWLEDGED", "RESOLVED"}


def create_alert(db: Session, alert_in: AlertCreate) -> Alert:
    # 1. Validate station
    station = None
    if alert_in.station_id is not None:
        station = db.query(Station).filter(Station.id == alert_in.station_id).first()
    elif alert_in.station_code is not None:
        station = get_station_by_id_or_code(db, alert_in.station_code)

    if not station:
        raise ValueError("Station not found")

    # 2. Validate sensor if provided
    sensor = None
    if alert_in.sensor_id is not None:
        sensor = db.query(Sensor).filter(Sensor.id == alert_in.sensor_id).first()
        if not sensor:
            raise ValueError("Sensor not found")
    elif alert_in.sensor_code is not None:
        sensor = db.query(Sensor).filter(Sensor.sensor_code == alert_in.sensor_code).first()
        if not sensor:
            raise ValueError("Sensor not found")

    if sensor and sensor.station_id != station.id:
        raise ValueError(
            f"Sensor '{sensor.sensor_code}' does not belong to station '{station.station_code}'"
        )

    severity = alert_in.severity.upper() if alert_in.severity else "MEDIUM"
    if severity not in VALID_SEVERITIES:
        severity = "MEDIUM"

    alert = Alert(
        station_id=station.id,
        sensor_id=sensor.id if sensor else None,
        severity=severity,
        alert_type=alert_in.alert_type or "GENERIC",
        title=alert_in.title,
        message=alert_in.message,
        anomaly_score=alert_in.anomaly_score,
        created_at=datetime.now(timezone.utc),
        status="ACTIVE",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def list_alerts_by_station(
    db: Session,
    station_id_or_code: str | int,
    status: str | None = None,
    limit: int = 100,
) -> list[Alert]:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        raise ValueError(f"Station '{station_id_or_code}' not found")

    query = db.query(Alert).filter(Alert.station_id == station.id)
    if status:
        query = query.filter(Alert.status == status.upper())

    return query.order_by(desc(Alert.created_at), desc(Alert.id)).limit(limit).all()


def get_alert_by_id(db: Session, alert_id: int) -> Alert | None:
    return db.query(Alert).filter(Alert.id == alert_id).first()


def acknowledge_alert(db: Session, alert_id: int) -> Alert:
    alert = get_alert_by_id(db, alert_id)
    if not alert:
        raise ValueError(f"Alert '{alert_id}' not found")

    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert(db: Session, alert_id: int) -> Alert:
    alert = get_alert_by_id(db, alert_id)
    if not alert:
        raise ValueError(f"Alert '{alert_id}' not found")

    alert.status = "RESOLVED"
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert
