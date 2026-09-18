# Backend Integration Readiness Audit (Polarix SIH26060 - Step 44)

**Audit Timestamp (UTC):** 2026-09-18T10:10:23.535018+00:00  
**Scope:** Person C (Machine Learning Specialist)  
**Target Audience:** Person A (Backend Engineer) & Person B (Frontend Engineer)  
**Status:** `ML_BOUNDARY_READY__BACKEND_COMPONENTS_PENDING`  

---

## 1. Architectural Boundary Map

```text
Telemetry Source (Simulator / Sensor Stream)
      │
      ▼
MQTT / Simulator Ingestion        [ NOT IMPLEMENTED in branch Rex (Person A) ]
      │
      ▼
FastAPI REST Endpoints            [ NOT IMPLEMENTED in branch Rex (Person A) ]
      │
      ▼
Telemetry Contract Adapter        [ FULLY IMPLEMENTED & VALIDATED (Person C) ]
      │  └─ adapt_backend_input(payload)
      ▼
ML Inference Service              [ FULLY IMPLEMENTED & VALIDATED (Person C) ]
      │  ├─ MaitriMLService (MTR) / BharatiMLService (BRT)
      │  ├─ 30-step sliding window buffer per sensor
      │  ├─ LSTM Autoencoder PyTorch reconstruction
      │  └─ Deterministic anomaly-type classification
      ▼
Backend Contract Output Adapter   [ FULLY IMPLEMENTED & VALIDATED (Person C) ]
      │  └─ adapt_backend_output(inference_result)
      ▼
Backend Rules & Severity Alerts   [ NOT IMPLEMENTED in branch Rex (Person A) ]
      │
      ▼
SQLite Persistence / EventBus     [ NOT IMPLEMENTED in branch Rex (Person A) ]
      │
      ▼
WebSocket Server Fanout           [ NOT IMPLEMENTED in branch Rex (Person A) ]
      │
      ▼
Frontend 3D Digital Twin (React)  [ NOT IMPLEMENTED in branch Rex (Person B) ]
```

---

## 2. Integration Readiness Matrix

| Architectural Boundary | Implementation State | Testability | Current Repository Evidence | Primary Owner | Status |
| :--- | :---: | :---: | :--- | :---: | :---: |
| **Telemetry Schema Normalization** | `FULLY IMPLEMENTED` | `TESTABLE` | `ml/inference/maitri_backend_contract.py, ml/inference/bharati_backend_contract.py` | Person C (ML) / Person A (Backend) | **`VALIDATED`** |
| **ML Inference Invocation** | `FULLY IMPLEMENTED` | `TESTABLE` | `MaitriMLService, BharatiMLService, process_backend_payload()` | Person C (ML) | **`VALIDATED`** |
| **FastAPI HTTP Ingestion Endpoints** | `NOT IMPLEMENTED IN CURRENT BRANCH` | `UNTESTABLE` | `No main.py or routers in branch Rex` | Person A (Backend) | **`NOT IMPLEMENTED`** |
| **MQTT Telemetry Ingestion** | `NOT IMPLEMENTED IN CURRENT BRANCH` | `UNTESTABLE` | `No MQTT client or broker subscriber in branch Rex` | Person A (Backend) | **`NOT IMPLEMENTED`** |
| **SQLite Persistence Layer** | `NOT IMPLEMENTED IN CURRENT BRANCH` | `UNTESTABLE` | `No database schema or SQLite ORM in branch Rex` | Person A (Backend) | **`NOT IMPLEMENTED`** |
| **EventBus Dispatcher** | `NOT IMPLEMENTED IN CURRENT BRANCH` | `UNTESTABLE` | `No event bus dispatcher in branch Rex` | Person A (Backend) | **`NOT IMPLEMENTED`** |
| **WebSocket Streaming** | `NOT IMPLEMENTED IN CURRENT BRANCH` | `UNTESTABLE` | `No WebSocket router in branch Rex` | Person A (Backend) | **`NOT IMPLEMENTED`** |
| **Frontend 3D Digital Twin Consumption** | `NOT IMPLEMENTED IN CURRENT BRANCH` | `UNTESTABLE` | `No frontend components in branch Rex` | Person B (Frontend) | **`NOT IMPLEMENTED`** |

---

## 3. In-Process ML Smoke Test Results

The ML subsystem was exercised through an in-process smoke test simulating end-to-end backend streaming workloads:

| Stage # | Stage Name | Status | Latency (ms) | Description |
| :---: | :--- | :---: | :---: | :--- |
| **1** | Schema Ingestion & Normalization | **`PASS`** | 0.0329 | Validated dictionary and raw JSON parsing into typed TelemetryInput / BharatiTelemetryInput contracts. |
| **2** | Cold-Start Warmup Progression | **`PASS`** | 0.6770 | Confirmed steps 1..29 bypass neural inference and return INSUFFICIENT_DATA with null score. |
| **3** | Nominal Scored Inference | **`PASS`** | 9.9061 | MTR score: 0.000259 (threshold=0.017674), BRT score: 0.000452 (threshold=0.013215307652775843). |
| **4** | SPIKE Anomaly Classification | **`PASS`** | 1.2687 | Verified sudden 60C shock jump triggers ANOMALY status and SPIKE classification on both stations. |
| **5** | DRIFT Ramp Anomaly Detection | **`PASS`** | 1.4528 | MTR drift status: ANOMALY (DRIFT), BRT drift status: ANOMALY (DRIFT). |
| **6** | STUCK_VALUE Detection & Recovery | **`PASS`** | 41.6532 | Flatline STUCK_VALUE observed: (MTR=True, BRT=True), Recovery released stuck state: True. |
| **7** | MISSING_DATA Ingestion & Buffer Flush | **`PASS`** | 0.6741 | MISSING quality returned MISSING_DATA and successfully flushed rolling buffer length from 30 to 0. |
| **8** | Multi-Sensor Stream Isolation & Output Schema | **`PASS`** | 4.1158 | Verified individual sensor isolation (TEMP_001 anomaly does not bleed to PRESS_001) and all 11 canonical fields survive strict JSON serialization. |

---

## 4. Integration Blueprint for Person A (Backend Integration Guide)

### Recommended Ingestion Hook (FastAPI Lifespan):

```python
# In backend/app/main.py or backend service lifespan:
from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.bharati_ml_service import BharatiMLService
from ml.inference.maitri_backend_contract import process_backend_payload as process_mtr
from ml.inference.bharati_backend_contract import process_backend_payload as process_brt

# Initialize singleton instances on startup
maitri_ml = MaitriMLService()
bharati_ml = BharatiMLService()

def handle_incoming_telemetry(payload: dict) -> dict:
    station = payload.get('station_id')
    if station == 'MTR':
        return process_mtr(maitri_ml, payload)
    elif station == 'BRT':
        return process_brt(bharati_ml, payload)
    else:
        raise ValueError(f'Unsupported station: {station}')
```

### Canonical Output Contract (11 Fields):

```json
{
  "station_id": "MTR",
  "sensor_id": "TEMP_001",
  "timestamp": "2026-09-18T10:30:00Z",
  "value": -15.2,
  "unit": "C",
  "quality": "GOOD",
  "source": "SIMULATOR",
  "anomaly_score": 0.004123,
  "anomaly_status": "NORMAL",
  "anomaly_type": "NORMAL",
  "model_version": "lstm-ae-v1"
}
```
