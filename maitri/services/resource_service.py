from datetime import datetime, timezone
from sqlalchemy.orm import Session

from maitri.models.resource import Resource
from maitri.models.station import Station
from maitri.schemas.resource import ResourceCreate, ResourceUpdate
from maitri.services.station_service import get_station_by_id_or_code

VALID_RESOURCE_TYPES = {
    "DIESEL",
    "BATTERY",
    "WATER",
    "FOOD",
    "MEDICAL",
    "SPARE_PARTS",
}
VALID_RESOURCE_STATUSES = {"NORMAL", "LOW", "WARNING", "CRITICAL"}


def create_resource(db: Session, resource_in: ResourceCreate) -> Resource:
    station = None
    if resource_in.station_id is not None:
        station = db.query(Station).filter(Station.id == resource_in.station_id).first()
    elif resource_in.station_code is not None:
        station = get_station_by_id_or_code(db, resource_in.station_code)

    if not station:
        raise ValueError("Station not found")

    resource_type = resource_in.resource_type.upper()

    if resource_in.current_quantity < 0:
        raise ValueError("Current quantity cannot be negative")
    if resource_in.capacity <= 0:
        raise ValueError("Capacity must be greater than zero")
    if resource_in.current_quantity > resource_in.capacity:
        raise ValueError("Current quantity cannot exceed capacity")

    status = (
        resource_in.status.upper()
        if resource_in.status and resource_in.status.upper() in VALID_RESOURCE_STATUSES
        else "NORMAL"
    )

    resource = Resource(
        station_id=station.id,
        resource_type=resource_type,
        current_quantity=resource_in.current_quantity,
        capacity=resource_in.capacity,
        consumption_rate=resource_in.consumption_rate,
        unit=resource_in.unit,
        status=status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def list_resources_by_station(
    db: Session, station_id_or_code: str | int
) -> list[Resource]:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        raise ValueError(f"Station '{station_id_or_code}' not found")

    return (
        db.query(Resource)
        .filter(Resource.station_id == station.id)
        .order_by(Resource.id)
        .all()
    )


def get_resource_by_id(db: Session, resource_id: int) -> Resource | None:
    return db.query(Resource).filter(Resource.id == resource_id).first()


def update_resource(
    db: Session, resource_id: int, resource_update: ResourceUpdate
) -> Resource:
    resource = get_resource_by_id(db, resource_id)
    if not resource:
        raise ValueError(f"Resource '{resource_id}' not found")

    new_capacity = (
        resource_update.capacity
        if resource_update.capacity is not None
        else resource.capacity
    )
    new_quantity = (
        resource_update.current_quantity
        if resource_update.current_quantity is not None
        else resource.current_quantity
    )

    if new_capacity <= 0:
        raise ValueError("Capacity must be greater than zero")
    if new_quantity < 0:
        raise ValueError("Current quantity cannot be negative")
    if new_quantity > new_capacity:
        raise ValueError("Current quantity cannot exceed capacity")

    if resource_update.capacity is not None:
        resource.capacity = resource_update.capacity
    if resource_update.current_quantity is not None:
        resource.current_quantity = resource_update.current_quantity
    if resource_update.consumption_rate is not None:
        resource.consumption_rate = resource_update.consumption_rate
    if resource_update.unit is not None:
        resource.unit = resource_update.unit
    if resource_update.status is not None:
        status_val = resource_update.status.upper()
        if status_val in VALID_RESOURCE_STATUSES:
            resource.status = status_val

    resource.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(resource)
    return resource


def seed_default_resources(db: Session) -> None:
    """Seed baseline resources for Maitri and Bharati if not already seeded."""
    default_resources = [
        # Maitri (MTR)
        {
            "station_code": "MTR",
            "resource_type": "DIESEL",
            "current_quantity": 45000.0,
            "capacity": 60000.0,
            "consumption_rate": 350.0,
            "unit": "L",
            "status": "NORMAL",
        },
        {
            "station_code": "MTR",
            "resource_type": "BATTERY",
            "current_quantity": 85.0,
            "capacity": 100.0,
            "consumption_rate": 1.2,
            "unit": "%",
            "status": "NORMAL",
        },
        {
            "station_code": "MTR",
            "resource_type": "WATER",
            "current_quantity": 12000.0,
            "capacity": 20000.0,
            "consumption_rate": 450.0,
            "unit": "L",
            "status": "NORMAL",
        },
        {
            "station_code": "MTR",
            "resource_type": "FOOD",
            "current_quantity": 180.0,
            "capacity": 365.0,
            "consumption_rate": 1.0,
            "unit": "days",
            "status": "NORMAL",
        },
        {
            "station_code": "MTR",
            "resource_type": "MEDICAL",
            "current_quantity": 95.0,
            "capacity": 100.0,
            "consumption_rate": 0.1,
            "unit": "%",
            "status": "NORMAL",
        },
        {
            "station_code": "MTR",
            "resource_type": "SPARE_PARTS",
            "current_quantity": 120.0,
            "capacity": 150.0,
            "consumption_rate": 0.5,
            "unit": "units",
            "status": "NORMAL",
        },
        # Bharati (BHR)
        {
            "station_code": "BHR",
            "resource_type": "DIESEL",
            "current_quantity": 52000.0,
            "capacity": 70000.0,
            "consumption_rate": 400.0,
            "unit": "L",
            "status": "NORMAL",
        },
        {
            "station_code": "BHR",
            "resource_type": "BATTERY",
            "current_quantity": 90.0,
            "capacity": 100.0,
            "consumption_rate": 1.0,
            "unit": "%",
            "status": "NORMAL",
        },
        {
            "station_code": "BHR",
            "resource_type": "WATER",
            "current_quantity": 16000.0,
            "capacity": 25000.0,
            "consumption_rate": 500.0,
            "unit": "L",
            "status": "NORMAL",
        },
        {
            "station_code": "BHR",
            "resource_type": "FOOD",
            "current_quantity": 240.0,
            "capacity": 365.0,
            "consumption_rate": 1.0,
            "unit": "days",
            "status": "NORMAL",
        },
        {
            "station_code": "BHR",
            "resource_type": "MEDICAL",
            "current_quantity": 98.0,
            "capacity": 100.0,
            "consumption_rate": 0.1,
            "unit": "%",
            "status": "NORMAL",
        },
        {
            "station_code": "BHR",
            "resource_type": "SPARE_PARTS",
            "current_quantity": 140.0,
            "capacity": 180.0,
            "consumption_rate": 0.5,
            "unit": "units",
            "status": "NORMAL",
        },
    ]

    for item in default_resources:
        station = get_station_by_id_or_code(db, item["station_code"])
        if not station:
            continue
        existing = (
            db.query(Resource)
            .filter(
                Resource.station_id == station.id,
                Resource.resource_type == item["resource_type"],
            )
            .first()
        )
        if not existing:
            resource = Resource(
                station_id=station.id,
                resource_type=item["resource_type"],
                current_quantity=item["current_quantity"],
                capacity=item["capacity"],
                consumption_rate=item["consumption_rate"],
                unit=item["unit"],
                status=item["status"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(resource)
    db.commit()


SEVERITY_ORDER = {"NORMAL": 0, "LOW": 1, "WARNING": 2, "CRITICAL": 3}


def _merge_risk(calculated_risk: str, current_status: str) -> str:
    c_val = SEVERITY_ORDER.get(calculated_risk.upper(), 0)
    s_val = SEVERITY_ORDER.get(current_status.upper(), 0)
    return calculated_risk.upper() if c_val >= s_val else current_status.upper()


def calculate_resource_forecast(resource: Resource) -> dict:
    current_quantity = resource.current_quantity
    capacity = resource.capacity
    consumption_rate = resource.consumption_rate
    unit = resource.unit
    status = resource.status or "NORMAL"

    if current_quantity <= 0:
        estimated_days = 0.0
        estimated_hours = 0.0
        risk_level = "CRITICAL"
        forecast_message = (
            f"Resource '{resource.resource_type}' is completely depleted (0.0 {unit}). Immediate replenishment required."
        )
    elif consumption_rate <= 0:
        estimated_days = None
        estimated_hours = None
        pct = (current_quantity / capacity) * 100.0 if capacity > 0 else 0.0
        if pct <= 10.0:
            calc_risk = "CRITICAL"
        elif pct <= 25.0:
            calc_risk = "WARNING"
        elif pct <= 40.0:
            calc_risk = "LOW"
        else:
            calc_risk = "NORMAL"
        risk_level = _merge_risk(calc_risk, status)
        forecast_message = (
            f"Zero consumption rate reported. Reserve at {pct:.1f}% ({current_quantity:.1f}/{capacity:.1f} {unit})."
        )
    else:
        estimated_days = round(current_quantity / consumption_rate, 2)
        estimated_hours = round(estimated_days * 24.0, 2)
        if estimated_days <= 2.0:
            calc_risk = "CRITICAL"
        elif estimated_days <= 7.0:
            calc_risk = "WARNING"
        elif estimated_days <= 14.0:
            calc_risk = "LOW"
        else:
            calc_risk = "NORMAL"
        risk_level = _merge_risk(calc_risk, status)
        forecast_message = (
            f"Estimated {estimated_days:.1f} days ({estimated_hours:.1f} hours) remaining at consumption rate of {consumption_rate:.1f} {unit}/day."
        )

    return {
        "resource_id": resource.id,
        "station_id": resource.station_id,
        "resource_type": resource.resource_type,
        "current_quantity": current_quantity,
        "capacity": capacity,
        "consumption_rate": consumption_rate,
        "unit": unit,
        "estimated_hours_remaining": estimated_hours,
        "estimated_days_remaining": estimated_days,
        "risk_level": risk_level,
        "forecast_message": forecast_message,
    }


def get_resource_forecast(db: Session, resource_id: int) -> dict:
    resource = get_resource_by_id(db, resource_id)
    if not resource:
        raise ValueError(f"Resource '{resource_id}' not found")
    return calculate_resource_forecast(resource)


def get_station_resources_forecast(
    db: Session, station_id_or_code: str | int
) -> list[dict]:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        raise ValueError(f"Station '{station_id_or_code}' not found")

    resources = (
        db.query(Resource)
        .filter(Resource.station_id == station.id)
        .order_by(Resource.id)
        .all()
    )
    return [calculate_resource_forecast(r) for r in resources]

