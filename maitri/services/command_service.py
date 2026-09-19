from datetime import datetime, timezone
import json
from typing import Any
import uuid
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from maitri.models.command import Command
from maitri.models.station import Station
from maitri.schemas.command import CommandCreate
from maitri.services.alert_service import acknowledge_alert, resolve_alert
from maitri.services.station_service import get_station_by_id_or_code
from maitri.services.sync_service import set_network_offline, set_network_online_and_sync
from maitri.simulator import get_supported_scenarios


def create_command(db: Session, command_in: CommandCreate) -> Command:
    station_id = None
    if command_in.station_id is not None:
        station = db.query(Station).filter(Station.id == command_in.station_id).first()
        if not station:
            raise ValueError("Station not found")
        station_id = station.id
    elif command_in.station_code is not None:
        station = get_station_by_id_or_code(db, command_in.station_code)
        if not station:
            raise ValueError("Station not found")
        station_id = station.id

    cmd_id = command_in.command_id or f"CMD-{uuid.uuid4().hex[:8].upper()}"

    payload_str = None
    if command_in.payload is not None:
        if isinstance(command_in.payload, (dict, list)):
            payload_str = json.dumps(command_in.payload)
        else:
            payload_str = str(command_in.payload)

    cmd = Command(
        command_id=cmd_id,
        station_id=station_id,
        command_type=command_in.command_type.upper(),
        status="PENDING",
        payload=payload_str,
        result_message=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(cmd)
    db.commit()
    db.refresh(cmd)
    return cmd


def get_command_by_id_or_code(
    db: Session, command_id: str | int
) -> Command | None:
    if isinstance(command_id, int) or (
        isinstance(command_id, str) and command_id.isdigit()
    ):
        int_id = int(command_id)
        cmd = (
            db.query(Command)
            .filter(
                or_(
                    Command.id == int_id,
                    Command.command_id == str(command_id),
                )
            )
            .first()
        )
        if cmd:
            return cmd
    return db.query(Command).filter(Command.command_id == str(command_id)).first()


def list_commands(
    db: Session,
    station_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[Command]:
    query = db.query(Command)
    if station_id is not None:
        query = query.filter(Command.station_id == station_id)
    if status is not None:
        query = query.filter(Command.status == status.upper())
    return query.order_by(desc(Command.created_at), desc(Command.id)).limit(limit).all()


def execute_command(db: Session, command_id: str | int) -> Command:
    cmd = get_command_by_id_or_code(db, command_id)
    if not cmd:
        raise ValueError("Command not found")

    payload_data: Any = None
    if cmd.payload:
        try:
            payload_data = json.loads(cmd.payload)
        except Exception:
            payload_data = cmd.payload

    cmd_type = cmd.command_type.upper()

    if cmd_type == "START_SCENARIO":
        scenario = None
        if isinstance(payload_data, dict):
            scenario = payload_data.get("scenario") or payload_data.get("scenario_name")
        elif isinstance(payload_data, str):
            scenario = payload_data

        supported = get_supported_scenarios()
        if not scenario or scenario.upper() not in supported:
            cmd.status = "FAILED"
            cmd.result_message = f"Execution failed: Unknown scenario '{scenario}'. Supported: {supported}"
            cmd.executed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(cmd)
            return cmd

        cmd.status = "EXECUTED"
        cmd.result_message = f"Scenario '{scenario.upper()}' started successfully."
        cmd.executed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cmd)
        return cmd

    elif cmd_type == "STOP_SCENARIO":
        cmd.status = "EXECUTED"
        cmd.result_message = "Scenario stopped successfully."
        cmd.executed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cmd)
        return cmd

    elif cmd_type == "SET_NETWORK_OFFLINE":
        set_network_offline(db)
        cmd.status = "EXECUTED"
        cmd.result_message = "Network set to OFFLINE."
        cmd.executed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cmd)
        return cmd

    elif cmd_type in ("SET_NETWORK_ONLINE", "REQUEST_SYNC"):
        res = set_network_online_and_sync(db)
        cmd.status = "EXECUTED"
        cmd.result_message = f"Network restored to ONLINE. Synced {res['synced_now']} pending records."
        cmd.executed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cmd)
        return cmd

    elif cmd_type == "ACKNOWLEDGE_ALERT":
        alert_id = None
        if isinstance(payload_data, dict):
            alert_id = payload_data.get("alert_id")
        elif isinstance(payload_data, int):
            alert_id = payload_data
        elif isinstance(payload_data, str) and payload_data.isdigit():
            alert_id = int(payload_data)

        if not alert_id:
            cmd.status = "FAILED"
            cmd.result_message = "Execution failed: 'alert_id' is required in payload."
            cmd.executed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(cmd)
            return cmd

        try:
            alert = acknowledge_alert(db, alert_id)
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")
            cmd.status = "EXECUTED"
            cmd.result_message = f"Alert {alert_id} acknowledged successfully."
            cmd.executed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(cmd)
            return cmd
        except Exception as exc:
            cmd.status = "FAILED"
            cmd.result_message = f"Execution failed: {exc}"
            cmd.executed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(cmd)
            return cmd

    elif cmd_type == "RESOLVE_ALERT":
        alert_id = None
        if isinstance(payload_data, dict):
            alert_id = payload_data.get("alert_id")
        elif isinstance(payload_data, int):
            alert_id = payload_data
        elif isinstance(payload_data, str) and payload_data.isdigit():
            alert_id = int(payload_data)

        if not alert_id:
            cmd.status = "FAILED"
            cmd.result_message = "Execution failed: 'alert_id' is required in payload."
            cmd.executed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(cmd)
            return cmd

        try:
            alert = resolve_alert(db, alert_id)
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")
            cmd.status = "EXECUTED"
            cmd.result_message = f"Alert {alert_id} resolved successfully."
            cmd.executed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(cmd)
            return cmd
        except Exception as exc:
            cmd.status = "FAILED"
            cmd.result_message = f"Execution failed: {exc}"
            cmd.executed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(cmd)
            return cmd

        cmd.status = "FAILED"
        cmd.result_message = f"Unsupported command type: {cmd.command_type}"
        cmd.executed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(cmd)

    # Log command event
    try:
        from maitri.services.event_service import log_event
        if cmd.station_id:
            log_event(
                db=db,
                station_id_or_code=cmd.station_id,
                event_type="COMMAND_EXECUTED",
                description=f"Command '{cmd.command_type}': {cmd.status}",
                severity="INFO" if cmd.status == "EXECUTED" else "LOW",
                source="COMMAND_SYSTEM",
                details={"command_id": cmd.command_id, "command_type": cmd.command_type, "status": cmd.status, "message": cmd.result_message},
            )
    except Exception:
        pass

    return cmd
