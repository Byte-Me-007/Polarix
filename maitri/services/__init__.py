"""Maitri Services Package."""

from maitri.services.alert_service import (
    acknowledge_alert,
    create_alert,
    get_alert_by_id,
    list_alerts_by_station,
    resolve_alert,
)
from maitri.services.command_service import (
    create_command,
    execute_command,
    get_command_by_id_or_code,
    list_commands,
)
from maitri.services.demo_service import (
    get_station_scenario_status,
    reset_demo_state,
    run_full_demo_sequence,
    start_station_scenario,
    stop_station_scenario,
)
from maitri.services.device_service import (
    create_device,
    get_device_by_device_id,
    get_device_by_id,
    list_devices,
)
from maitri.services.energy_service import get_station_energy_optimization
from maitri.services.event_service import list_events_by_station, log_event
from maitri.services.readiness_service import calculate_mission_readiness
from maitri.services.ml_adapter import (
    ML_STATUS_CONNECTED,
    ML_STATUS_NOT_CONNECTED,
    MLAdapter,
    ml_adapter,
)
from maitri.services.mqtt_service import (
    build_station_telemetry_topic,
    ingest_mqtt_telemetry,
    parse_sensor_message,
    parse_station_telemetry_topic,
    parse_telemetry_message,
)
from maitri.services.resource_service import (
    calculate_resource_forecast,
    create_resource,
    get_resource_by_id,
    get_resource_forecast,
    get_station_resources_forecast,
    list_resources_by_station,
    seed_default_resources,
    update_resource,
)
from maitri.services.sensor_service import (
    create_sensor_reading,
    list_sensor_readings,
)
from maitri.services.station_service import (
    get_sensors_by_station,
    get_station_by_id_or_code,
    list_stations,
    seed_default_stations,
)
from maitri.services.sync_service import (
    get_network_status,
    get_sync_status,
    is_network_online,
    reset_network_state,
    set_network_offline,
    set_network_online_and_sync,
    set_network_status,
)
from maitri.services.telemetry_service import (
    create_telemetry,
    get_latest_telemetry_by_station,
    get_telemetry_by_station,
)
from maitri.services.websocket_manager import ConnectionManager, manager
from maitri.simulator import (
    generate_telemetry_batch,
    get_supported_scenarios,
    publish_simulated_telemetry,
    serialize_telemetry_payload,
)

__all__ = [
    "acknowledge_alert",
    "create_alert",
    "get_alert_by_id",
    "list_alerts_by_station",
    "resolve_alert",
    "create_device",
    "get_device_by_device_id",
    "get_device_by_id",
    "list_devices",
    "create_sensor_reading",
    "list_sensor_readings",
    "parse_sensor_message",
    "build_station_telemetry_topic",
    "parse_station_telemetry_topic",
    "parse_telemetry_message",
    "ingest_mqtt_telemetry",
    "ConnectionManager",
    "manager",
    "list_stations",
    "get_station_by_id_or_code",
    "get_sensors_by_station",
    "seed_default_stations",
    "create_telemetry",
    "get_telemetry_by_station",
    "get_latest_telemetry_by_station",
    "create_resource",
    "list_resources_by_station",
    "get_resource_by_id",
    "update_resource",
    "seed_default_resources",
    "calculate_resource_forecast",
    "get_resource_forecast",
    "get_station_resources_forecast",
    "get_station_energy_optimization",
    "generate_telemetry_batch",
    "get_supported_scenarios",
    "publish_simulated_telemetry",
    "serialize_telemetry_payload",
    "get_network_status",
    "set_network_status",
    "is_network_online",
    "reset_network_state",
    "get_sync_status",
    "set_network_offline",
    "set_network_online_and_sync",
    "create_command",
    "get_command_by_id_or_code",
    "list_commands",
    "execute_command",
    "start_station_scenario",
    "stop_station_scenario",
    "get_station_scenario_status",
    "run_full_demo_sequence",
    "reset_demo_state",
]






