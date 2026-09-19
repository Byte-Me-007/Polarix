"""Mission Readiness Service.

Computes the single source of truth for Station Mission Readiness deterministically
from live backend subsystem states:
- environment (weather telemetry & limits)
- energy (generator power, solar, battery & optimization mode)
- structure (vibration and strain gauges)
- connectivity (satellite link & store-and-forward queue)
- supplies (fuel, food, water, medical reserves & burn rate)
- active alerts (critical, high, and medium operational alarms)

Does NOT use client-side or static mock formulas.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from maitri.schemas.readiness import MissionReadinessResponse, SubsystemReadiness
from maitri.services.alert_service import list_alerts_by_station
from maitri.services.energy_service import get_station_energy_optimization
from maitri.services.resource_service import get_station_resources_forecast
from maitri.services.station_service import get_station_by_id_or_code
from maitri.services.sync_service import get_network_status, is_network_online
from maitri.services.telemetry_service import get_latest_telemetry_by_station


def calculate_mission_readiness(
    db: Session, station_id_or_code: str | int
) -> MissionReadinessResponse:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        raise ValueError(f"Station '{station_id_or_code}' not found")

    critical_factors: list[str] = []

    # 1. ENVIRONMENT SUBSYSTEM
    telemetry_list = get_latest_telemetry_by_station(db, station.id)
    env_score = 100.0
    env_details = []

    for t in telemetry_list:
        code = t.sensor.sensor_code if t.sensor else ""
        domain = t.sensor.domain if t.sensor else ""
        if domain == "ENVIRONMENT":
            if t.quality == "BAD" or t.quality == "OFFLINE":
                env_score = min(env_score, 30.0)
                critical_factors.append(f"Environmental sensor {code} quality {t.quality}")
            elif t.quality == "WARNING":
                env_score = min(env_score, 65.0)

            # Domain threshold checks
            if "TMP" in code and (t.value < -45.0 or t.value > 10.0):
                env_score = min(env_score, 60.0)
                env_details.append(f"Extreme temperature: {t.value}°C")
            if "WND" in code and t.value > 30.0:
                env_score = min(env_score, 40.0 if t.value > 45.0 else 60.0)
                env_details.append(f"Severe wind gusts: {t.value} m/s")

    env_status = (
        "OPERATIONAL"
        if env_score >= 85
        else ("DEGRADED" if env_score >= 70 else ("AT_RISK" if env_score >= 50 else "CRITICAL"))
    )
    env_summary = "; ".join(env_details) if env_details else "Weather and atmospheric parameters nominal"

    # 2. ENERGY SUBSYSTEM
    energy_opt = get_station_energy_optimization(db, station.id)
    energy_score = 100.0
    energy_details = []

    current_status = energy_opt.get("current_energy_status", "OPTIMAL")
    recommended_mode = energy_opt.get("recommended_mode", "STANDARD_BALANCED")
    diesel_pct = energy_opt.get("diesel_reserve_pct", 100.0)
    battery_pct = energy_opt.get("battery_reserve_pct", 100.0)

    if current_status == "CRITICAL" or recommended_mode == "POWER_CRISIS_MINIMAL":
        energy_score = 25.0
        critical_factors.append("Power generation critical or insufficient")
        energy_details.append("Power crisis state")
    elif current_status == "DEGRADED" or recommended_mode == "FUEL_CONSERVATION":
        energy_score = 60.0
        energy_details.append("Fuel conservation active")

    # Evaluate live energy sensors (e.g. generator output and faults)
    for t in telemetry_list:
        code = t.sensor.sensor_code if t.sensor else ""
        domain = t.sensor.domain if t.sensor else ""
        if domain == "ENERGY":
            if "GEN" in code:
                if t.quality in ("BAD", "OFFLINE"):
                    energy_score = min(energy_score, 30.0)
                    critical_factors.append(f"Primary generator {code} fault (quality {t.quality})")
                    energy_details.append(f"Primary generator fault ({t.value} kW)")
                elif t.quality == "WARNING" or t.value < 50.0:
                    energy_score = min(energy_score, 60.0)
                    energy_details.append(f"Low generator output ({t.value} kW)")
            elif "SOL" in code:
                if t.quality in ("BAD", "OFFLINE"):
                    energy_score = min(energy_score, 65.0)

    if diesel_pct < 25.0:
        energy_score = min(energy_score, 35.0)
        critical_factors.append(f"Diesel fuel critically low ({diesel_pct:.1f}%)")
    elif diesel_pct < 40.0:
        energy_score = min(energy_score, 65.0)

    if battery_pct < 25.0:
        energy_score = min(energy_score, 40.0)
        critical_factors.append(f"Battery storage critically drained ({battery_pct:.1f}%)")

    energy_status = (
        "OPERATIONAL"
        if energy_score >= 85
        else ("DEGRADED" if energy_score >= 70 else ("AT_RISK" if energy_score >= 50 else "CRITICAL"))
    )
    energy_summary = "; ".join(energy_details) if energy_details else f"Power generation balanced ({recommended_mode})"

    # 3. STRUCTURE SUBSYSTEM
    struct_score = 100.0
    struct_details = []
    for t in telemetry_list:
        code = t.sensor.sensor_code if t.sensor else ""
        domain = t.sensor.domain if t.sensor else ""
        if domain == "STRUCTURE":
            if t.quality in ("BAD", "OFFLINE"):
                struct_score = min(struct_score, 35.0)
                critical_factors.append(f"Structural sensor {code} quality {t.quality}")
            elif t.quality == "WARNING":
                struct_score = min(struct_score, 65.0)

            if "VIB" in code and t.value > 25.0:
                struct_score = min(struct_score, 40.0 if t.value > 40.0 else 65.0)
                struct_details.append(f"Excess foundation vibration: {t.value} mm/s")
            if "STN" in code and abs(t.value) > 800.0:
                struct_score = min(struct_score, 50.0)
                struct_details.append(f"High structural strain: {t.value} µε")

    struct_status = (
        "OPERATIONAL"
        if struct_score >= 85
        else ("DEGRADED" if struct_score >= 70 else ("AT_RISK" if struct_score >= 50 else "CRITICAL"))
    )
    struct_summary = "; ".join(struct_details) if struct_details else "Foundation and superstructure integrity stable"

    # 4. CONNECTIVITY SUBSYSTEM
    net_status = get_network_status()
    if net_status == "ONLINE":
        conn_score = 100.0
        conn_status = "OPERATIONAL"
        conn_details = "Satellite communication link operational and synchronized"
    elif net_status == "SYNCING":
        conn_score = 80.0
        conn_status = "DEGRADED"
        conn_details = "Synchronizing backlog records with central command"
    else:  # OFFLINE
        conn_score = 45.0
        conn_status = "AT_RISK"
        conn_details = "Satellite blackout; local edge buffering active"
        critical_factors.append("Satellite communication offline")

    # 5. SUPPLIES SUBSYSTEM
    forecasts = get_station_resources_forecast(db, station.id)
    supplies_score = 100.0
    supplies_details = []

    for f in forecasts:
        r_type = f.get("resource_type")
        risk = f.get("risk_level", "NORMAL")
        days = f.get("estimated_days_remaining", 999.0)

        if risk == "CRITICAL" or days < 30.0:
            supplies_score = min(supplies_score, 30.0)
            critical_factors.append(f"{r_type} reserves critical ({days:.0f} days remaining)")
        elif risk == "WARNING" or days < 60.0:
            supplies_score = min(supplies_score, 65.0)
            supplies_details.append(f"{r_type} low ({days:.0f} days)")

    supplies_status = (
        "OPERATIONAL"
        if supplies_score >= 85
        else ("DEGRADED" if supplies_score >= 70 else ("AT_RISK" if supplies_score >= 50 else "CRITICAL"))
    )
    supplies_summary = "; ".join(supplies_details) if supplies_details else "All essential station resource reserves nominal"

    # 6. ACTIVE ALERTS EVALUATION
    active_alerts = list_alerts_by_station(db, station.id, status="ACTIVE", limit=200)
    alert_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for a in active_alerts:
        sev = a.severity.upper() if a.severity else "INFO"
        if sev in alert_counts:
            alert_counts[sev] += 1

    alert_penalty = (
        alert_counts["CRITICAL"] * 25.0
        + alert_counts["HIGH"] * 12.0
        + alert_counts["MEDIUM"] * 5.0
        + alert_counts["LOW"] * 2.0
    )
    alert_score = max(0.0, 100.0 - alert_penalty)

    for a in active_alerts:
        if a.severity in ("CRITICAL", "HIGH"):
            critical_factors.append(f"{a.severity} Alert: {a.title}")

    # WEIGHTED COMPOSITE CALCULATION
    # Environment: 15%, Energy: 25%, Structure: 15%, Connectivity: 15%, Supplies: 20%, Alerts: 10%
    raw_composite = (
        0.15 * env_score
        + 0.25 * energy_score
        + 0.15 * struct_score
        + 0.15 * conn_score
        + 0.20 * supplies_score
        + 0.10 * alert_score
    )

    # SAFETY RULES & OVERRIDES
    if alert_counts["CRITICAL"] > 0:
        # Cannot be OPERATIONAL if there is an active critical alert
        raw_composite = min(raw_composite, 65.0)

    if energy_score <= 30.0:
        # Power crisis caps total readiness
        raw_composite = min(raw_composite, 55.0)

    final_score = round(max(0.0, min(100.0, raw_composite)), 1)

    if final_score >= 85.0:
        overall_status = "OPERATIONAL"
    elif final_score >= 70.0:
        overall_status = "DEGRADED"
    elif final_score >= 50.0:
        overall_status = "AT_RISK"
    else:
        overall_status = "CRITICAL"

    subsystems = {
        "environment": SubsystemReadiness(
            name="Environmental & Meteorological",
            status=env_status,
            score=env_score,
            details=env_summary,
        ),
        "energy": SubsystemReadiness(
            name="Power Generation & Microgrid",
            status=energy_status,
            score=energy_score,
            details=energy_summary,
        ),
        "structure": SubsystemReadiness(
            name="Structural Integrity & Geotechnical",
            status=struct_status,
            score=struct_score,
            details=struct_summary,
        ),
        "connectivity": SubsystemReadiness(
            name="Satellite Communications & Store-and-Forward",
            status=conn_status,
            score=conn_score,
            details=conn_details,
        ),
        "supplies": SubsystemReadiness(
            name="Logistics & Life Support Consumables",
            status=supplies_status,
            score=supplies_score,
            details=supplies_summary,
        ),
    }

    return MissionReadinessResponse(
        station_id=station.id,
        station_code=station.station_code,
        overall_status=overall_status,
        readiness_score=final_score,
        subsystems=subsystems,
        active_alerts_count=alert_counts,
        critical_factors=critical_factors[:6],
        timestamp=datetime.now(timezone.utc),
    )
