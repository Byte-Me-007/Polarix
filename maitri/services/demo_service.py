from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session

from maitri.schemas.command import CommandCreate
from maitri.schemas.telemetry import TelemetryCreate
from maitri.services.alert_service import list_alerts_by_station
from maitri.services.command_service import create_command, execute_command
from maitri.services.energy_service import get_station_energy_optimization
from maitri.services.resource_service import get_station_resources_forecast
from maitri.services.station_service import get_station_by_id_or_code
from maitri.services.sync_service import (
    get_network_status,
    get_sync_status,
    set_network_offline,
    set_network_online_and_sync,
)
from maitri.services.telemetry_service import create_telemetry
from maitri.simulator import generate_telemetry_batch, get_supported_scenarios

# In-memory registry of active station demo scenarios
_active_scenarios: dict[int, dict[str, Any]] = {}


def reset_demo_state() -> None:
    """Reset all active scenario records."""
    global _active_scenarios
    _active_scenarios.clear()


def start_station_scenario(
    db: Session,
    station_id_or_code: str | int,
    scenario_name: str,
    step: int = 0,
) -> dict[str, Any]:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        raise ValueError(f"Station '{station_id_or_code}' not found")

    sc_name = scenario_name.upper()
    supported = get_supported_scenarios()
    if sc_name not in supported:
        raise ValueError(
            f"Unknown scenario '{scenario_name}'. Supported scenarios: {supported}"
        )

    # Automatic network mode adjustment for outage/recovery scenarios
    if sc_name == "SATELLITE_OUTAGE":
        set_network_offline(db)
    elif sc_name == "RECOVERY":
        set_network_online_and_sync(db)

    # Track active scenario state
    _active_scenarios[station.id] = {
        "scenario": sc_name,
        "started_at": datetime.now(timezone.utc),
        "is_active": True,
    }

    # Record and execute audit command
    try:
        cmd = create_command(
            db,
            CommandCreate(
                station_id=station.id,
                command_type="START_SCENARIO",
                payload={"scenario": sc_name, "step": step},
            ),
        )
        execute_command(db, cmd.id)
    except Exception:
        pass

    # Generate telemetry batch and ingest
    batch = generate_telemetry_batch(
        station.station_code, scenario=sc_name, step=step
    )
    for item in batch:
        create_telemetry(db, TelemetryCreate(**item))

    active_alerts = list_alerts_by_station(db, station.id, status="ACTIVE")
    sync_stats = get_sync_status(db)
    energy_opt = get_station_energy_optimization(db, station.id)
    resources_forecast = get_station_resources_forecast(db, station.id)

    return {
        "station_id": station.id,
        "station_code": station.station_code,
        "scenario_name": sc_name,
        "status": "RUNNING",
        "is_active": True,
        "telemetry_generated_count": len(batch),
        "active_alerts_count": len(active_alerts),
        "sync_status": sync_stats,
        "energy_optimization": energy_opt,
        "resource_forecast_summary": resources_forecast,
        "message": f"Scenario '{sc_name}' started successfully on station {station.station_code}.",
    }



def stop_station_scenario(
    db: Session, station_id_or_code: str | int
) -> dict[str, Any]:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        raise ValueError(f"Station '{station_id_or_code}' not found")

    _active_scenarios[station.id] = {
        "scenario": None,
        "started_at": None,
        "is_active": False,
    }

    try:
        cmd = create_command(
            db,
            CommandCreate(
                station_id=station.id,
                command_type="STOP_SCENARIO",
            ),
        )
        execute_command(db, cmd.id)
    except Exception:
        pass

    active_alerts = list_alerts_by_station(db, station.id, status="ACTIVE")
    return {
        "station_id": station.id,
        "station_code": station.station_code,
        "active_scenario": None,
        "is_active": False,
        "started_at": None,
        "message": f"Scenario stopped for station {station.station_code}.",
        "sync_status": get_network_status(),
        "active_alerts_count": len(active_alerts),
    }


def get_station_scenario_status(
    db: Session, station_id_or_code: str | int
) -> dict[str, Any]:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        raise ValueError(f"Station '{station_id_or_code}' not found")

    active_info = _active_scenarios.get(
        station.id, {"scenario": None, "started_at": None, "is_active": False}
    )
    active_alerts = list_alerts_by_station(db, station.id, status="ACTIVE")

    return {
        "station_id": station.id,
        "station_code": station.station_code,
        "active_scenario": active_info["scenario"],
        "is_active": active_info["is_active"],
        "started_at": active_info["started_at"],
        "message": (
            f"Active scenario: {active_info['scenario']}"
            if active_info["is_active"]
            else "No active scenario running."
        ),
        "sync_status": get_network_status(),
        "active_alerts_count": len(active_alerts),
    }


def run_full_demo_sequence(
    db: Session, station_id_or_code: str | int
) -> dict[str, Any]:
    station = get_station_by_id_or_code(db, station_id_or_code)
    if not station:
        raise ValueError(f"Station '{station_id_or_code}' not found")

    phases = [
        ("Phase 1: Baseline Operations", "NORMAL_DAY"),
        ("Phase 2: Blizzard Storm Event", "STORM"),
        ("Phase 3: Power Crisis & Generator Fluctuation", "POWER_CRISIS"),
        ("Phase 4: Satellite Comms Outage", "SATELLITE_OUTAGE"),
        ("Phase 5: Uplink Recovery & Telemetry Sync", "RECOVERY"),
    ]

    phase_results = []
    for idx, (phase_title, sc) in enumerate(phases, start=1):
        res = start_station_scenario(db, station.id, sc, step=idx)
        phase_results.append(
            {
                "phase": phase_title,
                "scenario_name": sc,
                "telemetry_ingested_count": res["telemetry_generated_count"],
                "network_status": res["sync_status"]["network_status"],
                "pending_sync_count": res["sync_status"]["pending_count"],
                "active_alerts_count": res["active_alerts_count"],
                "energy_mode": res["energy_optimization"].get("recommended_mode"),
                "message": res["message"],
            }
        )

    final_sync = get_sync_status(db)
    final_energy = get_station_energy_optimization(db, station.id)

    return {
        "station_id": station.id,
        "station_code": station.station_code,
        "total_phases": len(phases),
        "phases": phase_results,
        "final_sync_status": final_sync,
        "final_energy_optimization": final_energy,
        "message": f"Complete 5-phase SIH demo sequence executed successfully for station {station.station_code}.",
    }
