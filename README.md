# Polarix

## Maitri Backend

### Setup & Run Instructions

1. **Create virtual environment:**
   ```bash
   /opt/homebrew/bin/python3 -m venv .venv
   ```

2. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run tests:**
   ```bash
   pytest
   ```

5. **Run the Maitri backend:**
   ```bash
   uvicorn maitri.main:app --reload
   ```

6. **Health check URL:**
   ```text
   http://127.0.0.1:8000/health
   ```

## Maitri Smoke Test

The smoke test verifies the HTTP API endpoints (`/health`, `/devices/`, `/sensor-readings/ingest`, `/sensor-readings/device/{device_id}`) as well as the real-time WebSocket endpoint:
`ws://127.0.0.1:8000/ws/sensor-readings`

1. **Start server:**
   ```bash
   uvicorn maitri.main:app --reload
   ```

2. **In another terminal:**
   ```bash
   python scripts/smoke_test_maitri.py
   ```

## Antarctic Stations & Sensors Foundation

The backend provides station and sensor tracking for Antarctic research bases (**Maitri (`MTR`)** and **Bharati (`BHR`)**):

- **List all stations:**
  `GET /stations`
- **Get station details (by ID or station code):**
  `GET /stations/{station_id}` (e.g. `GET /stations/MTR` or `GET /stations/BHR`)
- **Get sensors for a station:**
  `GET /stations/{station_id}/sensors` (e.g. `GET /stations/MTR/sensors`)

Representative sensors span four core domains:
- **`ENVIRONMENT`**: Ambient temperature, wind speed, humidity, barometric pressure.
- **`STRUCTURE`**: Building foundation vibration, superstructure strain, roof tilt inclinometers.
- **`ENERGY`**: Diesel generator output, battery storage bank voltage, solar array generation.
- **`LOGISTICS`**: Main fuel storage tank level, fresh water reservoir levels.

## Station-Based Telemetry Endpoints

Ingest and query operational telemetry connected directly to configured stations and sensors:

- **Ingest Telemetry:**
  `POST /telemetry`
  ```json
  {
    "station_code": "MTR",
    "sensor_code": "MTR-ENV-TMP-01",
    "value": -18.5,
    "quality": "GOOD",
    "source": "SIMULATOR",
    "anomaly_score": 0.05
  }
  ```
- **Get Station Telemetry History:**
  `GET /stations/{station_id}/telemetry` (e.g. `GET /stations/MTR/telemetry?limit=50`)
- **Get Latest Station Telemetry (per sensor):**
  `GET /stations/{station_id}/telemetry/latest` (e.g. `GET /stations/MTR/telemetry/latest`)

Quality support: `GOOD`, `WARNING`, `BAD`, `UNKNOWN`, `OFFLINE`.
Source support: `SIMULATOR`, `MQTT`, `API`.

## Station-Based Alert Endpoints

Manage operational alerts across Antarctic stations:

- **List Station Alerts:**
  `GET /stations/{station_id}/alerts` (e.g. `GET /stations/MTR/alerts?status=ACTIVE&limit=50`)
- **Acknowledge Alert:**
  `POST /alerts/{alert_id}/ack`
- **Resolve Alert:**
  `POST /alerts/{alert_id}/resolve`
- **Create Alert:**
  `POST /alerts`
  ```json
  {
    "station_code": "MTR",
    "sensor_code": "MTR-ENG-GEN-01",
    "severity": "HIGH",
    "alert_type": "POWER_ANOMALY",
    "title": "Generator Power Fluctuation",
    "message": "Unstable generator voltage output detected"
  }
  ```

Severity support: `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
Status support: `ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`.
Automatic alert generation: Telemetry ingested with `BAD` quality automatically creates a `HIGH` severity fault alert; `OFFLINE` quality creates a `CRITICAL` severity offline alert.

## Station Resource Inventory Endpoints

Track critical station resources across research bases (Diesel, Battery, Water, Food, Medical supplies, Spare parts):

- **List Station Resources:**
  `GET /stations/{station_id}/resources` (e.g. `GET /stations/MTR/resources`)
- **Create Resource:**
  `POST /resources`
  ```json
  {
    "station_code": "MTR",
    "resource_type": "WATER",
    "current_quantity": 12000.0,
    "capacity": 20000.0,
    "consumption_rate": 450.0,
    "unit": "L",
    "status": "NORMAL"
  }
  ```
- **Update Resource:**
  `PATCH /resources/{resource_id}`
  ```json
  {
    "current_quantity": 10500.0,
    "status": "LOW",
    "consumption_rate": 480.0
  }
  ```

Resource types: `DIESEL`, `BATTERY`, `WATER`, `FOOD`, `MEDICAL`, `SPARE_PARTS`.
Resource statuses: `NORMAL`, `LOW`, `WARNING`, `CRITICAL`.

## Resource Forecasting Endpoints

Forecast resource depletion time and assess risk levels across Antarctic station inventory:

- **Get Station Resources Forecast:**
  `GET /stations/{station_id}/resources/forecast` (e.g. `GET /stations/MTR/resources/forecast`)
- **Get Single Resource Forecast:**
  `GET /resources/{resource_id}/forecast`

Risk Levels:
- **`CRITICAL`**: 0 quantity or estimated days remaining $\le$ 2 days (or reserve $\le$ 10%).
- **`WARNING`**: Estimated days remaining $\le$ 7 days (or reserve $\le$ 25%).
- **`LOW`**: Estimated days remaining $\le$ 14 days (or reserve $\le$ 40%).
- **`NORMAL`**: Estimated days remaining $>$ 14 days.

## Station Energy Optimization Endpoints

Generates deterministic station-level recommendations for generator load, battery reserve buffers, and renewable solar prioritization:

- **Get Station Energy Optimization Recommendations:**
  `GET /stations/{station_id}/energy/optimization` (e.g. `GET /stations/MTR/energy/optimization`)

Example Response:
```json
{
  "station_id": 1,
  "current_energy_status": "OPTIMAL",
  "risk_level": "NORMAL",
  "recommended_mode": "STANDARD_BALANCED",
  "actions": [
    "Maintain standard dual-generator load-sharing profile",
    "Float charge battery storage banks at nominal maintenance voltage",
    "Maintain nominal baseline power distribution across all station sectors"
  ],
  "reason": "Energy reserves operating within nominal Antarctic parameters: Diesel reserve at 75.0% (128.6 days remaining), Battery storage at 85.0%.",
  "diesel_reserve_pct": 75.0,
  "battery_reserve_pct": 85.0,
  "solar_output_kw": 0.0,
  "estimated_diesel_days": 128.6
}
```

Recommended Modes:
- **`STANDARD_BALANCED`**: Nominal baseline generator load and battery maintenance.
- **`SOLAR_PRIORITY`**: High renewable solar available; throttles generator to standby and prioritizes battery storage charging.
- **`FUEL_CONSERVATION`**: Sub-nominal diesel buffer; sheds non-essential HVAC/lab loads and reduces generator base load.
- **`POWER_CRISIS_MINIMAL`**: Critical fuel/battery depletion; activates life-support-only power shedding.

## Python Telemetry Simulator & Scenario Engine

A deterministic time-series telemetry generator designed for Antarctic station research nodes (`MTR`, `BHR`):

### Supported Scenarios:
- **`NORMAL_DAY`**: Nominal operational readings with realistic cyclic environmental variations.
- **`STORM`**: Extreme wind spikes ($> 45$ m/s), temperature plunge, elevated structural strain/vibration, and near-zero solar output.
- **`POWER_CRISIS`**: Generator output collapse, depleted battery levels, critical fuel drop.
- **`SENSOR_FAILURE`**: Injects `BAD` or `OFFLINE` sensor readings with anomaly scores $\ge 0.95$.
- **`SATELLITE_OUTAGE`**: Generates valid readings marked with `synced = False` for offline queue verification.
- **`RECOVERY`**: Exponentially decays perturbed values back to nominal baseline levels.

### Programmatic Usage:
```python
from maitri.simulator import generate_telemetry_batch, publish_simulated_telemetry

# Generate a storm telemetry batch for Maitri
batch = generate_telemetry_batch("MTR", scenario="STORM", step=0)

# Publish batch to MQTT broker topic antarctic/MTR/telemetry
published = publish_simulated_telemetry("MTR", scenario="STORM", step=0, client=mqtt_client)
```

## MQTT Telemetry Ingestion & Publishing

Antarctic station telemetry can be published by simulators or field devices and ingested directly by the backend via MQTT.

### Topic Format
- `antarctic/{station_id}/telemetry`
  - Examples:
    - `antarctic/MTR/telemetry` (Maitri station telemetry)
    - `antarctic/BHR/telemetry` (Bharati station telemetry)

### MQTT Broker Configuration
Configurable via environment variables or `.env`:
- `MQTT_BROKER_HOST` (Default: `localhost`)
- `MQTT_BROKER_PORT` (Default: `1883`)
- `MQTT_TOPIC_PREFIX` (Default: `antarctic`)

### Ingestion Flow & Validations
Backend MQTT ingestion (`ingest_mqtt_telemetry`):
1. **Station Validation**: Verifies station code extracted from topic or payload exists in SQLite DB.
2. **Sensor Validation**: Verifies sensor code exists and belongs to the specified station.
3. **Storage**: Persists telemetry records with source `MQTT` or `SIMULATOR`.
4. **Alerts**: Automatically creates:
   - `HIGH` severity `SENSOR_FAULT` alert on `BAD` quality telemetry.
   - `CRITICAL` severity `SENSOR_OFFLINE` alert on `OFFLINE` quality telemetry.

## Offline Queue & Synchronization (Satellite Outage / Recovery)

Handles network disconnection, local queueing, and backlog synchronization when satellite uplinks go down and recover.

### Endpoints
- **Get Sync Status:**
  `GET /sync/status`
  ```json
  {
    "network_status": "ONLINE",
    "is_online": true,
    "pending_count": 0,
    "synced_count": 42,
    "total_count": 42,
    "last_sync_timestamp": "2026-09-18T23:26:00Z",
    "message": "Network is ONLINE. All telemetry records synchronized."
  }
  ```
- **Simulate Network Outage (Offline Mode):**
  `POST /demo/network/offline`
- **Simulate Network Recovery (Online & Sync):**
  `POST /demo/network/online`

### Queueing & Recovery Flow
1. **Offline Mode (`OFFLINE`)**:
   - All incoming telemetry records are stored locally in the database with `synced = False`.
   - Critical events and operational alerts (`BAD` / `OFFLINE` quality) continue to trigger and persist without loss.
2. **Online Recovery (`ONLINE` / `SYNCING`)**:
   - Replays and marks all pending records as `synced = True`.
   - Returns count of synchronized records (`synced_now`) and updates `last_sync_timestamp`.

## Command Handling Backend Foundation

A centralized command API designed for frontend control, demo execution, and station-level scenario triggering.

### Supported Command Types
- `START_SCENARIO`: Initiates simulator scenarios (`NORMAL_DAY`, `STORM`, `POWER_CRISIS`, `SENSOR_FAILURE`, `SATELLITE_OUTAGE`, `RECOVERY`).
- `STOP_SCENARIO`: Halts active scenario simulation.
- `SET_NETWORK_OFFLINE`: Switches network state to `OFFLINE` and begins local queueing.
- `SET_NETWORK_ONLINE` / `REQUEST_SYNC`: Restores network connectivity and reconciles all queued telemetry.
- `ACKNOWLEDGE_ALERT`: Acknowledges an active station alert.
- `RESOLVE_ALERT`: Resolves an alert.

### Endpoints
- **Create Command:**
  `POST /commands`
  ```json
  {
    "command_type": "START_SCENARIO",
    "station_code": "MTR",
    "payload": {
      "scenario": "STORM"
    }
  }
  ```
- **List Commands:**
  `GET /commands` (optional filters: `?station_id=1&status=PENDING&limit=50`)
- **Get Single Command:**
  `GET /commands/{command_id}` (e.g. `GET /commands/CMD-A1B2C3D4`)
- **Execute Command:**
  `POST /commands/{command_id}/execute`
  ```json
  {
    "id": 1,
    "command_id": "CMD-A1B2C3D4",
    "station_id": 1,
    "command_type": "START_SCENARIO",
    "status": "EXECUTED",
    "payload": {
      "scenario": "STORM"
    },
    "result_message": "Scenario 'STORM' started successfully.",
    "created_at": "2026-09-18T23:30:00Z",
    "executed_at": "2026-09-18T23:30:01Z"
  }
  ```

### Lifecycle States
- **`PENDING`**: Command created and queued for execution.
- **`EXECUTED`**: Successfully validated and executed.
- **`FAILED`**: Validation or runtime error occurred; failure reason preserved in `result_message`.

## SIH Demo Orchestration API

Judge-friendly orchestration controller that coordinates full operational scenarios, telemetry batches, alert triggers, sync states, energy optimization, and resource forecasts across Antarctic stations (`MTR`, `BHR`).

### Endpoints
- **Start Scenario:**
  `POST /demo/scenarios/{station_id}/{scenario_name}/start`
  - Validates station and scenario.
  - Automatically adapts network mode (`SATELLITE_OUTAGE` $\rightarrow$ `OFFLINE`, `RECOVERY` $\rightarrow$ `ONLINE` & sync).
  - Generates and ingests telemetry batch.
  - Returns complete station operational dashboard state.
- **Stop Scenario:**
  `POST /demo/scenarios/{station_id}/stop`
  - Halts active scenario simulation.
- **Get Scenario Status:**
  `GET /demo/scenarios/{station_id}/status`
  - Returns current active scenario, start time, sync status, and active alert count.
- **Run Full 5-Phase Demo Sequence:**
  `POST /demo/run/full-sequence/{station_id}`
  - Automatically executes the complete SIH demonstration timeline:
    1. **`NORMAL_DAY`**: Baseline nominal telemetry.
    2. **`STORM`**: Blizzard event with high wind gust warnings.
    3. **`POWER_CRISIS`**: Generator fluctuation and fuel conservation recommendations.
    4. **`SATELLITE_OUTAGE`**: Uplink severed, offline queueing activated, critical alerts preserved.
    5. **`RECOVERY`**: Network restored, pending backlog replayed and synchronized.

## Integration Contracts & Team Handoff

For the exhaustive specification with all schemas, models, and payloads, see [docs/INTEGRATION_CONTRACT.md](file:///Users/parthipan/Documents/Polarix_A/Polarix/docs/INTEGRATION_CONTRACT.md).

### Quick Handoff for Person B (Frontend Dashboard)
- **Dashboard Telemetry & Sensors**:
  - Stations list: `GET /stations`
  - Latest readings per station: `GET /stations/{station_id}/telemetry/latest`
  - Live sensor stream: WebSocket `ws://127.0.0.1:8000/ws/sensor-readings`
- **Resource Depletion Meters**:
  - Resource forecasts: `GET /stations/{station_id}/resources/forecast`
- **Energy Optimization Recommendations**:
  - Optimization mode & load actions: `GET /stations/{station_id}/energy/optimization`
- **Alert Center**:
  - Active alerts: `GET /stations/{station_id}/alerts?status=ACTIVE`
  - Acknowledge alert: `POST /alerts/{alert_id}/ack`
  - Resolve alert: `POST /alerts/{alert_id}/resolve`
- **Network Sync & Satellite Outage Indicator**:
  - Connection status & queue count: `GET /sync/status`
  - Offline mode trigger: `POST /demo/network/offline`
  - Online recovery & sync trigger: `POST /demo/network/online`
- **Demo Scenario Execution**:
  - 1-Click scenario start: `POST /demo/scenarios/{station_id}/{scenario_name}/start`
  - Full 5-Phase SIH demo run: `POST /demo/run/full-sequence/{station_id}`

### Quick Handoff for Person C (Machine Learning Integration)
- **Anomaly Score Injection**:
  - Ingest telemetry via `POST /telemetry` or MQTT topic `antarctic/{station_id}/telemetry`.
  - Include computed `anomaly_score` ($0.0 \le \text{score} \le 1.0$) and `quality` (`GOOD`, `WARNING`, `BAD`, `OFFLINE`).
- **Backend Autonomous Reactions**:
  - `quality == "BAD"` $\rightarrow$ Backend auto-creates `HIGH` severity `SENSOR_FAULT` alert containing the ML anomaly score.
  - `quality == "OFFLINE"` $\rightarrow$ Backend auto-creates `CRITICAL` severity `SENSOR_OFFLINE` alert.
  - Energy optimization engine automatically responds to degraded telemetry to shed non-vital loads.







