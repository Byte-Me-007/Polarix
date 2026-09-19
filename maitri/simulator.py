import json
import math
from datetime import datetime, timezone
from typing import Any

SUPPORTED_SCENARIOS = [
    "NORMAL_DAY",
    "STORM",
    "POWER_CRISIS",
    "SENSOR_FAILURE",
    "SATELLITE_OUTAGE",
    "RECOVERY",
]

# Baseline nominal sensor profiles for Antarctic stations
STATION_SENSOR_PROFILES: dict[str, list[dict[str, Any]]] = {
    "MTR": [
        {
            "sensor_code": "MTR-ENV-TMP-01",
            "domain": "ENVIRONMENT",
            "unit": "°C",
            "nominal_base": -20.0,
            "nominal_amplitude": 2.5,
            "min_val": -60.0,
            "max_val": 20.0,
        },
        {
            "sensor_code": "MTR-ENV-WND-01",
            "domain": "ENVIRONMENT",
            "unit": "m/s",
            "nominal_base": 12.0,
            "nominal_amplitude": 3.0,
            "min_val": 0.0,
            "max_val": 75.0,
        },
        {
            "sensor_code": "MTR-STR-VIB-01",
            "domain": "STRUCTURE",
            "unit": "mm/s",
            "nominal_base": 0.05,
            "nominal_amplitude": 0.02,
            "min_val": 0.0,
            "max_val": 50.0,
        },
        {
            "sensor_code": "MTR-ENG-GEN-01",
            "domain": "ENERGY",
            "unit": "kW",
            "nominal_base": 180.0,
            "nominal_amplitude": 10.0,
            "min_val": 0.0,
            "max_val": 250.0,
        },
        {
            "sensor_code": "MTR-LOG-FUL-01",
            "domain": "LOGISTICS",
            "unit": "%",
            "nominal_base": 75.0,
            "nominal_amplitude": 0.5,
            "min_val": 0.0,
            "max_val": 100.0,
        },
    ],
    "BHR": [
        {
            "sensor_code": "BHR-ENV-TMP-01",
            "domain": "ENVIRONMENT",
            "unit": "°C",
            "nominal_base": -15.0,
            "nominal_amplitude": 3.0,
            "min_val": -50.0,
            "max_val": 25.0,
        },
        {
            "sensor_code": "BHR-STR-STN-01",
            "domain": "STRUCTURE",
            "unit": "µε",
            "nominal_base": 120.0,
            "nominal_amplitude": 15.0,
            "min_val": -2000.0,
            "max_val": 2000.0,
        },
        {
            "sensor_code": "BHR-ENG-SOL-01",
            "domain": "ENERGY",
            "unit": "kW",
            "nominal_base": 45.0,
            "nominal_amplitude": 8.0,
            "min_val": 0.0,
            "max_val": 120.0,
        },
        {
            "sensor_code": "BHR-LOG-FUL-01",
            "domain": "LOGISTICS",
            "unit": "%",
            "nominal_base": 80.0,
            "nominal_amplitude": 0.5,
            "min_val": 0.0,
            "max_val": 100.0,
        },
    ],
}


def get_supported_scenarios() -> list[str]:
    """Return the list of all supported scenario identifiers."""
    return list(SUPPORTED_SCENARIOS)


def _compute_sensor_value(
    profile: dict[str, Any], scenario: str, step: int
) -> tuple[float, str, float | None, bool]:
    """
    Computes a realistic sensor value, quality, anomaly score, and sync status
    for a given scenario and time-series step.
    """
    base = profile["nominal_base"]
    amp = profile["nominal_amplitude"]
    code = profile["sensor_code"]
    domain = profile["domain"]

    # Natural cyclic variation based on step
    cyclic = amp * math.sin(step * 0.25)
    nominal_val = base + cyclic

    quality = "GOOD"
    anomaly_score = 0.02
    synced = True

    if scenario == "NORMAL_DAY":
        val = nominal_val
        quality = "GOOD"
        anomaly_score = 0.02

    elif scenario == "STORM":
        if "TMP" in code:
            # Temperature plunges in storm
            val = base - 22.0 - abs(cyclic)
            quality = "WARNING"
            anomaly_score = 0.65
        elif "WND" in code:
            # High storm winds (e.g. 45 - 60 m/s)
            val = base + 38.0 + abs(cyclic * 2.0)
            quality = "WARNING"
            anomaly_score = 0.85
        elif "VIB" in code or "STN" in code:
            # Elevated structural strain / vibration under high wind gusts
            val = (base * 5.0) + abs(cyclic)
            quality = "WARNING"
            anomaly_score = 0.70
        elif "SOL" in code:
            # Overcast / blizzard kills solar output
            val = max(0.0, cyclic * 0.1)
            quality = "GOOD"
            anomaly_score = 0.40
        else:
            val = nominal_val

    elif scenario == "POWER_CRISIS":
        if "GEN" in code:
            # Generator output drops or fluctuates severely
            val = max(15.0, base * 0.25 + cyclic)
            quality = "BAD"
            anomaly_score = 0.92
        elif "SOL" in code:
            val = 0.0
            quality = "WARNING"
            anomaly_score = 0.75
        elif "FUL" in code:
            # Depleted fuel reserve
            val = max(5.0, base * 0.15 - (step * 0.1))
            quality = "WARNING"
            anomaly_score = 0.80
        else:
            val = nominal_val

    elif scenario == "SENSOR_FAILURE":
        # Selected primary sensor fails with BAD quality or OFFLINE
        if "TMP" in code or "VIB" in code:
            val = -999.0
            quality = "BAD"
            anomaly_score = 0.99
        else:
            val = nominal_val

    elif scenario == "SATELLITE_OUTAGE":
        # Normal operations, but communications link down -> un-synced queue
        val = nominal_val
        synced = False
        quality = "GOOD"
        anomaly_score = 0.05

    elif scenario == "RECOVERY":
        # Readings transitioning back from perturbation to nominal
        decay = math.exp(-step * 0.2)
        if "TMP" in code:
            val = nominal_val - (15.0 * decay)
        elif "WND" in code:
            val = nominal_val + (20.0 * decay)
        elif "GEN" in code:
            val = nominal_val - (50.0 * decay)
        elif "STR" in code:
            val = nominal_val + (30.0 * decay)
        else:
            val = nominal_val
        quality = "GOOD"
        anomaly_score = round(0.15 * decay + 0.02, 3)

    else:
        val = nominal_val

    # Clamp value within sensor physical bounds if not an erroneous reading
    if quality != "BAD":
        val = max(profile["min_val"], min(profile["max_val"], val))

    return round(val, 2), quality, anomaly_score, synced


def generate_telemetry_batch(
    station_code: str,
    scenario: str = "NORMAL_DAY",
    step: int = 0,
    timestamp: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Generates a batch of telemetry records for all configured sensors of a station
    under a specific scenario.
    """
    st_code = station_code.upper()
    if st_code not in STATION_SENSOR_PROFILES:
        raise ValueError(
            f"Invalid station code '{station_code}'. Supported stations: {list(STATION_SENSOR_PROFILES.keys())}"
        )

    sc_name = scenario.upper()
    if sc_name not in SUPPORTED_SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{scenario}'. Supported scenarios: {SUPPORTED_SCENARIOS}"
        )

    ts = timestamp or datetime.now(timezone.utc)
    sensor_profiles = STATION_SENSOR_PROFILES[st_code]
    batch = []

    for profile in sensor_profiles:
        val, quality, anomaly_score, synced = _compute_sensor_value(
            profile, sc_name, step
        )
        record = {
            "station_code": st_code,
            "sensor_code": profile["sensor_code"],
            "value": val,
            "unit": profile["unit"],
            "quality": quality,
            "source": "SIMULATOR",
            "timestamp": ts,
            "anomaly_score": anomaly_score,
            "synced": synced,
        }
        batch.append(record)

    return batch


def serialize_telemetry_payload(record: dict[str, Any]) -> str:
    """Serialize a telemetry record dict to a JSON string with ISO timestamps."""
    data = dict(record)
    if isinstance(data.get("timestamp"), datetime):
        data["timestamp"] = data["timestamp"].isoformat()
    return json.dumps(data)


def publish_simulated_telemetry(
    station_code: str,
    scenario: str = "NORMAL_DAY",
    step: int = 0,
    timestamp: datetime | None = None,
    client: Any = None,
    broker_host: str | None = None,
    broker_port: int | None = None,
    topic_prefix: str | None = None,
) -> list[dict[str, Any]]:
    """
    Generates telemetry batch for a station under a given scenario,
    and publishes each record to the MQTT topic 'antarctic/{station_code}/telemetry'.
    Returns the list of generated payload dictionaries.
    """
    from maitri.services.mqtt_service import build_station_telemetry_topic

    topic = build_station_telemetry_topic(station_code, prefix=topic_prefix)
    batch = generate_telemetry_batch(
        station_code=station_code,
        scenario=scenario,
        step=step,
        timestamp=timestamp,
    )

    if client is not None:
        for record in batch:
            payload_str = serialize_telemetry_payload(record)
            client.publish(topic, payload_str)
    elif broker_host is not None:
        try:
            import paho.mqtt.client as paho_mqtt
            port = broker_port or 1883
            try:
                mqtt_client = paho_mqtt.Client(
                    paho_mqtt.CallbackAPIVersion.VERSION2
                )
            except AttributeError:
                mqtt_client = paho_mqtt.Client()
            mqtt_client.connect(broker_host, port, 60)
            for record in batch:
                payload_str = serialize_telemetry_payload(record)
                mqtt_client.publish(topic, payload_str)
            mqtt_client.disconnect()
        except Exception as exc:
            raise ConnectionError(
                f"Failed to publish to MQTT broker {broker_host}:{broker_port}: {exc}"
            ) from exc

    return batch

