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

