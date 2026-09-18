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




