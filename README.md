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


