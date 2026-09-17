# Polarix Maitri ML Team Integration Checklist (SIH26060)

**Author:** Person C (ML Specialist)  
**Audience:** Person A (Backend Engineer), Person B (Frontend Engineer), and Platform Integrators  
**Station Scope:** Maitri (`MTR`)  
**Readiness Status:** Validated and Ready for Backend Consumption  
**Date:** 2026-09-18  

---

### 1. Backend → ML Input

Person A's backend (FastAPI, MQTT ingestion worker, or simulation runner) streams telemetry records into the ML layer. Telemetry can be provided as a Python dictionary or JSON string with the following fields:

```json
{
  "station_id": "MTR",
  "sensor_id": "TEMP_001",
  "timestamp": "2026-09-17T10:30:00Z",
  "value": -34.5,
  "unit": "C",
  "quality": "GOOD",
  "source": "SIMULATOR"
}
```

#### Field Specifications:
- **`station_id`** (`str`): Must be strictly `"MTR"` (Maitri).
- **`sensor_id`** (`str`): Must be one of the 5 supported Maitri telemetry streams:
  - `TEMP_001`: Ambient / Structural Temperature (°C)
  - `PRESS_001`: Barometric Pressure (hPa)
  - `HUM_001`: Relative Humidity (%)
  - `VIB_001`: Generator Vibration (mm/s)
  - `POWER_001`: Power Generator Output (kW)
- **`timestamp`** (`str`): Standard ISO 8601 UTC timestamp string (e.g. `2026-09-17T10:30:00Z`).
- **`value`** (`float` or `null`): Sensor reading, or `None` if communication dropped.
- **`unit`** (`str`): Measurement unit (`"C"`, `"hPa"`, `"%"`, `"mm/s"`, `"kW"`).
- **`quality`** (`str`): Telemetry flag (`"GOOD"`, `"BAD"`, `"UNCERTAIN"`, `"MISSING"`).
- **`source`** (`str`): Telemetry source tag (e.g. `"SIMULATOR"`).

---

### 2. ML Processing

When telemetry is ingested by `MaitriMLService.process_telemetry()` or `process_backend_payload()`, the execution sequence follows:

1. **Input Validation**: `adapt_backend_input()` validates schema integrity, station (`MTR`), and sensor support.
2. **Per-Sensor History Isolation**: The observation is routed to an isolated 30-step sliding deque (`collections.deque(maxlen=30)`) dedicated to that sensor.
3. **LSTM Reconstruction Scoring**:
   - Observations 1 to 29 return status `"INSUFFICIENT_DATA"` with `anomaly_score = null`.
   - The 30th and subsequent valid observations scale the 30-step tensor and compute the Mean Squared Error (MSE) reconstruction loss via `lstm-ae-v1`.
4. **Threshold Comparison**: The MSE reconstruction error is compared against the frozen validation threshold (`0.017674`):
   - $MSE \le 0.017674 \implies$ `anomaly_status = "NORMAL"`
   - $MSE > 0.017674 \implies$ `anomaly_status = "ANOMALY"`
5. **Anomaly Type Classification**: If anomalous, the 30-step sequence is evaluated by `AnomalyTypeClassifier` to assign a physical category (`SPIKE`, `DRIFT`, `STUCK_VALUE`, `UNKNOWN`).
6. **Output Construction**: The pipeline packages outcomes into a typed `TelemetryInferenceOutput` and adapts it via `adapt_backend_output()` into a sanitized, JSON-serializable dictionary with guaranteed finite floating-point values.

---

### 3. ML → Backend Output

The adapted JSON response returned to Person A contains:

```json
{
  "station_id": "MTR",
  "sensor_id": "TEMP_001",
  "timestamp": "2026-09-17T10:30:00Z",
  "value": -34.5,
  "unit": "C",
  "quality": "GOOD",
  "source": "SIMULATOR",
  "anomaly_score": 0.002824,
  "anomaly_status": "NORMAL",
  "anomaly_type": "NORMAL",
  "model_version": "lstm-ae-v1"
}
```

When an anomaly occurs:
```json
{
  "station_id": "MTR",
  "sensor_id": "TEMP_001",
  "timestamp": "2026-09-17T10:30:00Z",
  "value": 25.0,
  "unit": "C",
  "quality": "GOOD",
  "source": "SIMULATOR",
  "anomaly_score": 4.945585,
  "anomaly_status": "ANOMALY",
  "anomaly_type": "SPIKE",
  "model_version": "lstm-ae-v1"
}
```

---

### 4. Edge Cases

| Scenario / Edge Case | System Behavior | Output Status | Output Score | Buffer State |
| :--- | :--- | :--- | :--- | :--- |
| **Warm-up ($< 30$ samples)** | Observation stored; scored inference withheld until 30 continuous records exist. | `INSUFFICIENT_DATA` | `null` | Increments (1 to 29). |
| **Missing Telemetry (`value = null`)** | Fast-path return. Gaps reset the sequence to avoid distorted synthetic jumps. | `MISSING_DATA` | `null` | **Flushed to 0**. |
| **Bad Quality (`quality != "GOOD"`)** | Fast-path return with buffer flush. | `MISSING_DATA` | `null` | **Flushed to 0**. |
| **Non-Finite (`NaN`, `+inf`, `-inf`)** | Intercepted before PyTorch tensors; routes cleanly to missing data. | `MISSING_DATA` | `null` | **Flushed to 0**. |
| **Duplicate Timestamp** | Raises `DuplicateTelemetryError`. | Exception | — | Preserved (not duplicated). |
| **Stale / Out-of-Order Timestamp** | Raises `StaleTelemetryError`. | Exception | — | Preserved in chronological order. |
| **Unsupported Station (non-`MTR`)** | Raises `UnsupportedStationError`. | Exception | — | Untouched. |
| **Unsupported Sensor** | Raises `UnsupportedSensorError`. | Exception | — | Untouched. |

---

### 5. Ownership Boundary

#### Person A (Backend Specialist):
- Backend infrastructure & application lifecycle (FastAPI).
- MQTT broker ingestion & client subscription handlers.
- Telemetry simulator runners & scenario engine execution.
- REST endpoints and WebSocket broadcasting to frontend.
- SQLite / PostgreSQL database models, migrations, and query optimization.
- Integration glue calling `process_backend_payload(ml_service, payload)`.

#### Person B (Frontend Specialist):
- React dashboard UI & layouts.
- Data visualization components and live streaming charts (ECharts).
- 3D Digital Twin station rendering and interactive equipment nodes.
- Client-side anomaly alert banners and operator notifications.

#### Person C (Machine Learning Specialist):
- ML models (Rolling Z-score baseline & LSTM Autoencoder).
- Model artifact versioning, manifest tracking, and SHA-256 cryptographic verification.
- Decision threshold calibration & trade-off analysis.
- Physical anomaly type heuristic classification rules.
- ML streaming inference service (`MaitriMLService`) and backend adapters (`maitri_backend_contract`).
- Comprehensive ML test suite, reliability hardening, and observability diagnostics.

---

### 6. Important ML Limitations

1. **Synthetic Telemetry Only**:
   - All ML models, baselines, calibrations, and benchmarks are based strictly on synthetic telemetry generated for Maitri station.
   - **DO NOT** claim validation against real-world Antarctic telemetry.
2. **No Field Operational / Certified Accuracy Claims**:
   - **DO NOT** claim "90%+ accuracy", "field-tested in Antarctica", or "production-grade mission critical reliability".
3. **LSTM False-Positive Tradeoff**:
   - The threshold (`0.017674`) prioritizes spike (100% recall) and drift (84.67% recall) sensitivity on the synthetic test set, incurring a **48.15% false positive rate** on normal diurnal fluctuations.
4. **STUCK_VALUE Sensitivity**:
   - The single-threshold MSE reconstruction loss is not sensitive to mid-range sensor flatlines (5% test recall; short stuck-value scenario evaluates as `NORMAL`). Dedicated variance heuristics are recommended for future production iterations.

---

### 7. Integration Sequence

The exact end-to-end integration dataflow:

```text
Person A telemetry JSON (MQTT / REST / Worker)
               ↓
     adapt_backend_input()
               ↓
        TelemetryInput (Validated)
               ↓
   MaitriMLService.process_telemetry()
               ↓
    LSTM Sequence Reconstruction
               ↓
      Anomaly Status Evaluation
               ↓
  Anomaly Type Physical Classification
               ↓
     TelemetryInferenceOutput (Typed)
               ↓
     adapt_backend_output()
               ↓
 Backend JSON Response (Emitted to WebSocket / DB)
```

#### One-Call Integration Snippet for Person A:
```python
# Startup:
from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.maitri_backend_contract import process_backend_payload

ml_service = MaitriMLService()  # Initialize singleton once

# Telemetry ingestion:
backend_response = process_backend_payload(ml_service, incoming_telemetry_dict)
```
