# Polarix Machine Learning Integration Kit for Person A (Backend Engineer)

**Project:** Polarix — Smart India Hackathon 2026 (Problem Statement SIH26060)  
**Author:** Person C — Machine Learning Specialist  
**Target Audience:** Person A — Backend Engineer (FastAPI / MQTT / SQLite / WebSockets)  
**Status:** `FINAL_INTEGRATION_READY`  
**Stations Covered:** Maitri (`MTR`) & Bharati (`BRT`)  

---

## 1. What Person A Receives from Person C

Person C provides the finalized, self-contained, CPU-optimized Machine Learning subsystem for real-time telemetry anomaly detection. 

Person A receives:
1. **Pre-trained Deep Learning Models**: Two PyTorch LSTM Autoencoders (`lstm-ae-v1` for Maitri, `lstm-ae-bharati-v1` for Bharati).
2. **Deterministic Anomaly Type Classifiers**: Physical rule engines categorizing anomalies into explainable classes (`SPIKE`, `DRIFT`, `STUCK_VALUE`, `NORMAL`, `UNKNOWN`).
3. **Stateful Rolling Window Inference Services**: `MaitriMLService` and `BharatiMLService` managing rolling 30-observation histories per sensor.
4. **Data Quality & Protection Guards**: Automated `MISSING_DATA` buffer flushes, and chronological `DuplicateTelemetryError` / `StaleTelemetryError` guards.
5. **Zero-Dependency Backend Contract Adapters**: Single-call functions (`process_backend_payload`) that ingest raw backend dictionary/JSON payloads and return canonical 11-field JSON responses with guaranteed finite floating-point values.

---

## 2. Exact Imports

Use the exact import paths defined below. All dependencies are standard PyTorch and NumPy (no FastAPI or Pydantic dependencies inside the ML layer):

```python
# 1. High-Level ML Services
from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.bharati_ml_service import BharatiMLService

# 2. Maitri Backend Contract Adapters
from ml.inference.maitri_backend_contract import (
    adapt_backend_input as adapt_mtr_input,
    adapt_backend_output as adapt_mtr_output,
    process_backend_payload as process_mtr_payload,
)

# 3. Bharati Backend Contract Adapters
from ml.inference.bharati_backend_contract import (
    adapt_backend_input as adapt_brt_input,
    adapt_backend_output as adapt_brt_output,
    process_backend_payload as process_brt_payload,
)

# 4. Typed Contract Exceptions (For backend error handling)
from ml.inference.inference_contract import (
    DuplicateTelemetryError as MaitriDuplicateError,
    StaleTelemetryError as MaitriStaleError,
    InvalidContractError as MaitriInvalidContractError,
    UnsupportedSensorError as MaitriUnsupportedSensorError,
    UnsupportedStationError as MaitriUnsupportedStationError,
)
from ml.inference.bharati_inference_contract import (
    DuplicateTelemetryError as BharatiDuplicateError,
    StaleTelemetryError as BharatiStaleError,
    InvalidContractError as BharatiInvalidContractError,
    UnsupportedSensorError as BharatiUnsupportedSensorError,
    UnsupportedStationError as BharatiUnsupportedStationError,
)
```

---

## 3. Service Lifecycle & Singleton Pattern

> [!WARNING]
> **CRITICAL LIFECYCLE RULE:**  
> **DO NOT instantiate a new `MaitriMLService` or `BharatiMLService` inside a request handler or MQTT callback.**  
> The inference service maintains an in-memory 30-observation rolling window buffer for each sensor. Re-instantiating the service on every incoming packet destroys the accumulated sequence history, causing all packets to perpetually return `INSUFFICIENT_DATA`.

### Recommended FastAPI Lifespan Implementation:

```python
# In backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.bharati_ml_service import BharatiMLService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize ML singletons once on server startup
    app.state.maitri_ml = MaitriMLService()
    app.state.bharati_ml = BharatiMLService()
    print("Polarix ML Services initialized and ready.")
    yield
    # Teardown logic if needed
    app.state.maitri_ml.reset_all()
    app.state.bharati_ml.reset_all()

app = FastAPI(lifespan=lifespan)
```

---

## 4. Telemetry → ML Processing Flow

The integration adapter handles schema validation, time synchronization, model execution, and JSON formatting in a single call:

```text
Backend Telemetry Packet (Dict / JSON)
               │
               ▼
   process_backend_payload()
               │
               ├── 1. adapt_backend_input()     ── Validates schema, station, and sensor channel
               ├── 2. service.process_telemetry() ── Stateful 30-step window + PyTorch forward pass
               └── 3. adapt_backend_output()    ── Sanitizes floats (no NaN/Inf) and formats 11 fields
               │
               ▼
Canonical 11-Field Output Dictionary (Ready for SQLite & WebSocket)
```

---

## 5. Maitri Integration Example (`MTR / TEMP_001`)

```python
from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.maitri_backend_contract import process_backend_payload

# 1. Initialize once
maitri_service = MaitriMLService()

# 2. Ingest telemetry point
raw_packet = {
    "station_id": "MTR",
    "sensor_id": "TEMP_001",
    "timestamp": "2026-09-18T10:00:30Z",
    "value": -15.2,
    "unit": "C",
    "quality": "GOOD",
    "source": "SIMULATOR"
}

result = process_backend_payload(maitri_service, raw_packet)

# Sequence Progression:
# - Observations 1 to 29: result["anomaly_status"] == "INSUFFICIENT_DATA", result["anomaly_score"] is None
# - Observation 30+:     result["anomaly_status"] == "NORMAL", result["anomaly_score"] <= 0.017674
# - Upon Shock Spike:    result["anomaly_status"] == "ANOMALY", result["anomaly_type"] == "SPIKE"
```

---

## 6. Bharati Integration Example (`BRT / BRT_TEMP_001`)

```python
from ml.inference.bharati_ml_service import BharatiMLService
from ml.inference.bharati_backend_contract import process_backend_payload

# 1. Initialize once
bharati_service = BharatiMLService()

# 2. Ingest telemetry point
raw_packet = {
    "station_id": "BRT",
    "sensor_id": "BRT_TEMP_001",
    "timestamp": "2026-09-18T10:00:30Z",
    "value": -10.5,
    "unit": "C",
    "quality": "GOOD",
    "source": "SIMULATOR"
}

result = process_backend_payload(bharati_service, raw_packet)

# Sequence Progression:
# - Observations 1 to 29: result["anomaly_status"] == "INSUFFICIENT_DATA", result["anomaly_score"] is None
# - Observation 30+:     result["anomaly_status"] == "NORMAL", result["anomaly_score"] <= 0.013215
# - Upon Frozen Flatline: result["anomaly_status"] == "ANOMALY", result["anomaly_type"] == "STUCK_VALUE"
```

---

## 7. Backend Station Routing Pattern

Person A can implement a simple station router:

```python
def ingest_telemetry_packet(app_state, payload: dict) -> dict:
    station_id = payload.get("station_id")
    
    if station_id == "MTR":
        return process_mtr_payload(app_state.maitri_ml, payload)
    elif station_id == "BRT":
        return process_brt_payload(app_state.bharati_ml, payload)
    else:
        raise ValueError(f"Unknown station_id '{station_id}'. Supported stations: ['MTR', 'BRT']")
```

### Supported Station & Sensor Channels:
- **Maitri (`MTR`)**: `TEMP_001`, `PRESS_001`, `HUM_001`, `VIB_001`, `POWER_001`
- **Bharati (`BRT`)**: `BRT_TEMP_001`, `BRT_PRESS_001`, `BRT_HUM_001`, `BRT_VIB_001`, `BRT_POWER_001`

---

## 8. Missing Data & Dropout Handling

When a sensor packet arrives with:
- `value: null` / `None`
- `value: NaN` or `Infinity`
- `quality: "MISSING"` / `"BAD"` / non-`"GOOD"`

### Established ML Contract Behavior:
1. **Status**: Emits `anomaly_status: "MISSING_DATA"` with `anomaly_score: null` and `anomaly_type: null`.
2. **Buffer Action**: Immediately flushes the rolling 30-observation window for that specific sensor to 0.
3. **Recovery**: Once valid telemetry resumes, the sensor cleanly re-enters `INSUFFICIENT_DATA` warmup until 30 consecutive valid points accumulate.

---

## 9. Duplicate & Stale Telemetry Protection

If a telemetry packet arrives with:
- A timestamp identical to the last recorded timestamp (`DuplicateTelemetryError`)
- A timestamp older than the last recorded timestamp (`StaleTelemetryError`)

### Exception Handling for Person A:

```python
try:
    result = process_mtr_payload(maitri_service, packet)
except MaitriDuplicateError as e:
    # Log warning and reject/ignore duplicate packet
    logger.warning("Duplicate telemetry packet rejected: %s", e)
except MaitriStaleError as e:
    # Log warning and reject out-of-order packet
    logger.warning("Out-of-order telemetry packet rejected: %s", e)
```

The rolling sequence history buffer is **never corrupted** when duplicate or stale packets are rejected.

---

## 10. Canonical 11-Field Output Contract

Every valid ML inference invocation emits a dictionary matching the following schema:

```json
{
  "station_id": "MTR",
  "sensor_id": "TEMP_001",
  "timestamp": "2026-09-18T10:00:30Z",
  "value": -15.0,
  "unit": "C",
  "quality": "GOOD",
  "source": "SIMULATOR",
  "anomaly_score": 0.00042,
  "anomaly_status": "NORMAL",
  "anomaly_type": "NORMAL",
  "model_version": "lstm-ae-v1"
}
```

### Vocabulary Guarantees:
- **`anomaly_status`**: `"NORMAL"`, `"ANOMALY"`, `"INSUFFICIENT_DATA"`, `"MISSING_DATA"`.
- **`anomaly_type`**: `"NORMAL"`, `"SPIKE"`, `"DRIFT"`, `"STUCK_VALUE"`, `"UNKNOWN"` (or `null` during warmup/dropout).
- **`anomaly_score`**: Finite `float` rounded to 6 decimal places (or `null` during warmup/dropout). Guaranteed **no `NaN` or `Inf`**.

---

## 11. Architectural Ownership Matrix

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Person C (Machine Learning Specialist) — FULLY DELIVERED & FROZEN      │
│  - PyTorch LSTM-AE model weights and configurations                    │
│  - Scaler normalization statistics                                     │
│  - Empirical decision thresholds (MTR: 0.017674, BRT: 0.013215)        │
│  - 30-step sliding window stateful rolling history                     │
│  - Explainable anomaly-type classification heuristics                  │
│  - Zero-dependency contract adapters (process_backend_payload)         │
└────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Person A (Backend Engineer) — TO BE IMPLEMENTED IN BACKEND             │
│  - FastAPI REST API & WebSocket server fanout                          │
│  - MQTT broker client & ingestion loop                                 │
│  - SQLite database persistence for canonical 11-field records          │
│  - Operational alert severity logic (e.g. HIGH/MEDIUM/LOW alerts)      │
│  - Simulator command dispatch & lifecycle                              │
└────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Person B (Frontend Engineer) — TO BE IMPLEMENTED IN UI                 │
│  - React dashboard with real-time charting                             │
│  - Three.js 3D Digital Twin station model                              │
│  - Live status indicators and anomaly alarm pills                      │
│  - Station toggle (Maitri vs Bharati)                                  │
└────────────────────────────────────────────────────────────────────────┘
```
