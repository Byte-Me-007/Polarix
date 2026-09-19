from sqlalchemy import func
from sqlalchemy.orm import Session

from maitri.models.sensor import Sensor
from maitri.models.station import Station


def list_stations(db: Session) -> list[Station]:
    return db.query(Station).all()


def get_station_by_id_or_code(
    db: Session, identifier: str | int
) -> Station | None:
    if isinstance(identifier, int) or (
        isinstance(identifier, str) and identifier.isdigit()
    ):
        station = db.query(Station).filter(Station.id == int(identifier)).first()
        if station:
            return station

    return (
        db.query(Station)
        .filter(func.upper(Station.station_code) == str(identifier).upper())
        .first()
    )


def get_sensors_by_station(
    db: Session, station_id_or_code: str | int
) -> list[Sensor]:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        return []
    return (
        db.query(Sensor)
        .filter(Sensor.station_id == station.id)
        .order_by(Sensor.id)
        .all()
    )


def seed_default_stations(db: Session):
    """Seed Maitri and Bharati stations with representative sensors if not already seeded."""
    default_stations_data = [
        {
            "station_code": "MTR",
            "station_name": "Maitri Station",
            "description": "India's second permanent research station in Antarctica, located at Schirmacher Oasis.",
            "latitude": -70.767,
            "longitude": 11.733,
            "status": "ACTIVE",
            "sensors": [
                {
                    "sensor_code": "MTR-ENV-TMP-01",
                    "sensor_name": "Maitri Ambient Temperature Sensor",
                    "domain": "ENVIRONMENT",
                    "unit": "°C",
                    "location_x": 0.0,
                    "location_y": 0.0,
                    "location_z": 2.5,
                    "criticality": "HIGH",                    "minimum_value": -60.0,
                    "maximum_value": 20.0,
                    "active": True,
                    "asset_id": "MET-MAST-01",
                    "zone": "EXTERIOR_MET",
                },
                {
                    "sensor_code": "MTR-ENV-WND-01",
                    "sensor_name": "Maitri Anemometer Wind Speed Sensor",
                    "domain": "ENVIRONMENT",
                    "unit": "m/s",
                    "location_x": 10.0,
                    "location_y": 5.0,
                    "location_z": 10.0,
                    "criticality": "HIGH",
                    "minimum_value": 0.0,
                    "maximum_value": 75.0,
                    "active": True,
                    "asset_id": "MET-MAST-01",
                    "zone": "EXTERIOR_MET",
                },
                {
                    "sensor_code": "MTR-STR-VIB-01",
                    "sensor_name": "Main Building Foundation Vibration Monitor",
                    "domain": "STRUCTURE",
                    "unit": "mm/s",
                    "location_x": 0.0,
                    "location_y": 0.0,
                    "location_z": 0.0,
                    "criticality": "MEDIUM",
                    "minimum_value": 0.0,
                    "maximum_value": 50.0,
                    "active": True,
                    "asset_id": "MAIN-MODULE-BLDG",
                    "zone": "ZONE_CENTRAL",
                },
                {
                    "sensor_code": "MTR-ENG-GEN-01",
                    "sensor_name": "Primary Diesel Generator Power Output",
                    "domain": "ENERGY",
                    "unit": "kW",
                    "location_x": -15.0,
                    "location_y": 20.0,
                    "location_z": 0.0,
                    "criticality": "CRITICAL",
                    "minimum_value": 0.0,
                    "maximum_value": 250.0,
                    "active": True,
                    "asset_id": "GENSET-DIESEL-01",
                    "zone": "ZONE_POWER",
                },
                {
                    "sensor_code": "MTR-LOG-FUL-01",
                    "sensor_name": "Main Fuel Storage Tank Level",
                    "domain": "LOGISTICS",
                    "unit": "%",
                    "location_x": -25.0,
                    "location_y": 30.0,
                    "location_z": 0.0,
                    "criticality": "CRITICAL",
                    "minimum_value": 0.0,
                    "maximum_value": 100.0,
                    "active": True,
                    "asset_id": "FUEL-FARM-TANK-01",
                    "zone": "ZONE_LOGISTICS",
                },
            ],
        },
        {
            "station_code": "BHR",
            "station_name": "Bharati Station",
            "description": "India's third permanent Antarctic research facility, located at Larsemann Hills.",
            "latitude": -69.407,
            "longitude": 76.195,
            "status": "ACTIVE",
            "sensors": [
                {
                    "sensor_code": "BHR-ENV-TMP-01",
                    "sensor_name": "Bharati Ambient Temperature Sensor",
                    "domain": "ENVIRONMENT",
                    "unit": "°C",
                    "location_x": 0.0,
                    "location_y": 0.0,
                    "location_z": 3.0,
                    "criticality": "HIGH",
                    "minimum_value": -50.0,
                    "maximum_value": 25.0,
                    "active": True,
                    "asset_id": "MET-MAST-02",
                    "zone": "EXTERIOR_MET",
                },
                {
                    "sensor_code": "BHR-STR-STN-01",
                    "sensor_name": "Superstructure Strain Gauge",
                    "domain": "STRUCTURE",
                    "unit": "µε",
                    "location_x": 5.0,
                    "location_y": 5.0,
                    "location_z": 6.0,
                    "criticality": "HIGH",
                    "minimum_value": -2000.0,
                    "maximum_value": 2000.0,
                    "active": True,
                    "asset_id": "MAIN-STRUCTURE",
                    "zone": "ZONE_STRUCTURE",
                },
                {
                    "sensor_code": "BHR-ENG-SOL-01",
                    "sensor_name": "Solar Array Generation Monitor",
                    "domain": "ENERGY",
                    "unit": "kW",
                    "location_x": 30.0,
                    "location_y": -10.0,
                    "location_z": 4.0,
                    "criticality": "MEDIUM",
                    "minimum_value": 0.0,
                    "maximum_value": 120.0,
                    "active": True,
                    "asset_id": "SOLAR-ARRAY-01",
                    "zone": "ZONE_RENEWABLES",
                },
                {
                    "sensor_code": "BHR-LOG-FUL-01",
                    "sensor_name": "Reserve Fuel Tank Level Monitor",
                    "domain": "LOGISTICS",
                    "unit": "%",
                    "location_x": -20.0,
                    "location_y": 15.0,
                    "location_z": 0.0,
                    "criticality": "CRITICAL",
                    "minimum_value": 0.0,
                    "maximum_value": 100.0,
                    "active": True,
                    "asset_id": "FUEL-FARM-TANK-02",
                    "zone": "ZONE_LOGISTICS",
                },
            ],
        },
    ]

    for st_data in default_stations_data:
        existing_station = (
            db.query(Station)
            .filter(Station.station_code == st_data["station_code"])
            .first()
        )
        if not existing_station:
            new_station = Station(
                station_code=st_data["station_code"],
                station_name=st_data["station_name"],
                description=st_data["description"],
                latitude=st_data["latitude"],
                longitude=st_data["longitude"],
                status=st_data["status"],
            )
            db.add(new_station)
            db.flush()

            for s_data in st_data["sensors"]:
                sensor = Sensor(
                    station_id=new_station.id,
                    sensor_code=s_data["sensor_code"],
                    sensor_name=s_data["sensor_name"],
                    domain=s_data["domain"],
                    unit=s_data["unit"],
                    location_x=s_data.get("location_x"),
                    location_y=s_data.get("location_y"),
                    location_z=s_data.get("location_z"),
                    criticality=s_data.get("criticality", "MEDIUM"),
                    minimum_value=s_data.get("minimum_value"),
                    maximum_value=s_data.get("maximum_value"),
                    active=s_data.get("active", True),
                    asset_id=s_data.get("asset_id"),
                    zone=s_data.get("zone"),
                )
                db.add(sensor)
        else:
            # Backfill asset_id and zone if missing
            for s_data in st_data["sensors"]:
                existing_sensor = (
                    db.query(Sensor)
                    .filter(Sensor.sensor_code == s_data["sensor_code"])
                    .first()
                )
                if existing_sensor:
                    if not existing_sensor.asset_id:
                        existing_sensor.asset_id = s_data.get("asset_id")
                    if not existing_sensor.zone:
                        existing_sensor.zone = s_data.get("zone")

    db.commit()
