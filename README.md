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
