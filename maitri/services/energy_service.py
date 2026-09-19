from sqlalchemy import desc
from sqlalchemy.orm import Session

from maitri.models.resource import Resource
from maitri.models.sensor import Sensor
from maitri.models.telemetry import Telemetry
from maitri.services.station_service import get_station_by_id_or_code


def get_station_energy_optimization(
    db: Session, station_id_or_code: str | int
) -> dict:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        raise ValueError(f"Station '{station_id_or_code}' not found")

    # 1. Fetch energy resources (Diesel & Battery)
    diesel = (
        db.query(Resource)
        .filter(
            Resource.station_id == station.id,
            Resource.resource_type == "DIESEL",
        )
        .first()
    )
    battery = (
        db.query(Resource)
        .filter(
            Resource.station_id == station.id,
            Resource.resource_type == "BATTERY",
        )
        .first()
    )

    # 2. Fetch latest solar generation telemetry if available
    solar_sensor = (
        db.query(Sensor)
        .filter(
            Sensor.station_id == station.id,
            Sensor.domain == "ENERGY",
            Sensor.sensor_code.contains("SOL"),
        )
        .first()
    )
    latest_solar = None
    if solar_sensor:
        latest_solar = (
            db.query(Telemetry)
            .filter(
                Telemetry.station_id == station.id,
                Telemetry.sensor_id == solar_sensor.id,
            )
            .order_by(desc(Telemetry.timestamp), desc(Telemetry.id))
            .first()
        )

    # 3. Calculate reserves and rates
    diesel_pct = (
        round((diesel.current_quantity / diesel.capacity) * 100.0, 1)
        if diesel and diesel.capacity > 0
        else None
    )
    diesel_days = (
        round(diesel.current_quantity / diesel.consumption_rate, 1)
        if diesel and diesel.consumption_rate > 0
        else None
    )
    battery_pct = (
        round(battery.current_quantity, 1)
        if battery
        else None
    )
    solar_kw = (
        round(float(latest_solar.value), 1)
        if latest_solar and latest_solar.value is not None
        else 0.0
    )

    diesel_status = diesel.status.upper() if diesel and diesel.status else "NORMAL"
    battery_status = battery.status.upper() if battery and battery.status else "NORMAL"

    # 4. Deterministic decision matrix
    if (
        (diesel_days is not None and diesel_days <= 2.0)
        or (diesel_pct is not None and diesel_pct <= 10.0)
        or (battery_pct is not None and battery_pct <= 15.0)
        or diesel_status == "CRITICAL"
        or battery_status == "CRITICAL"
    ):
        current_energy_status = "CRITICAL"
        risk_level = "CRITICAL"
        recommended_mode = "POWER_CRISIS_MINIMAL"
        actions = [
            "Shed non-critical scientific and laboratory electrical loads immediately",
            "Operate diesel generator at minimum threshold for life-support and heating only",
            "Preserve remaining battery storage strictly for emergency communications",
            "Activate emergency Antarctic fuel conservation protocol",
        ]
        reason = (
            f"Severe energy deficit detected at {station.station_name}: "
            f"Diesel reserve at {diesel_pct if diesel_pct is not None else 0.0}% "
            f"({diesel_days if diesel_days is not None else 0.0} days remaining), "
            f"Battery storage at {battery_pct if battery_pct is not None else 0.0}%."
        )

    elif (
        (diesel_days is not None and diesel_days <= 7.0)
        or (diesel_pct is not None and diesel_pct <= 30.0)
        or (battery_pct is not None and battery_pct <= 40.0)
        or diesel_status == "WARNING"
        or battery_status == "WARNING"
    ):
        current_energy_status = "DEGRADED"
        risk_level = "WARNING"
        recommended_mode = "FUEL_CONSERVATION"
        actions = [
            "Throttle generator base load output by 25%",
            "Maximize battery buffer utilization during peak generation hours",
            "Schedule heavy thermal cycles to coincide with secondary generation",
            "Adjust station habitat HVAC baseline setpoints by -2°C",
        ]
        reason = (
            f"Sub-optimal fuel reserve buffer detected: "
            f"Diesel reserve at {diesel_pct if diesel_pct is not None else 0.0}% "
            f"({diesel_days if diesel_days is not None else 0.0} days remaining). "
            f"Recommended fuel conservation."
        )

    elif (
        solar_kw >= 20.0
        and (battery_pct is None or battery_pct < 95.0)
        and (diesel_pct is None or diesel_pct > 30.0)
    ):
        current_energy_status = "OPTIMAL"
        risk_level = "NORMAL"
        recommended_mode = "SOLAR_PRIORITY"
        actions = [
            "Throttle diesel generator to idle standby to minimize fuel consumption",
            f"Channel active renewable solar output ({solar_kw:.1f} kW) to charge battery storage banks",
            "Run auxiliary water heating and wastewater purification during high solar generation",
        ]
        reason = (
            f"High renewable solar generation available ({solar_kw:.1f} kW). "
            f"Prioritizing renewable battery charging and generator standby."
        )

    else:
        current_energy_status = "OPTIMAL"
        risk_level = "NORMAL"
        recommended_mode = "STANDARD_BALANCED"
        actions = [
            "Maintain standard dual-generator load-sharing profile",
            "Float charge battery storage banks at nominal maintenance voltage",
            "Maintain nominal baseline power distribution across all station sectors",
        ]
        reason = (
            f"Energy reserves operating within nominal Antarctic parameters: "
            f"Diesel reserve at {diesel_pct if diesel_pct is not None else 0.0}% "
            f"({diesel_days if diesel_days is not None else 0.0} days remaining), "
            f"Battery storage at {battery_pct if battery_pct is not None else 0.0}%."
        )

    return {
        "station_id": station.id,
        "current_energy_status": current_energy_status,
        "risk_level": risk_level,
        "recommended_mode": recommended_mode,
        "actions": actions,
        "reason": reason,
        "diesel_reserve_pct": diesel_pct,
        "battery_reserve_pct": battery_pct,
        "solar_output_kw": solar_kw,
        "estimated_diesel_days": diesel_days,
    }
