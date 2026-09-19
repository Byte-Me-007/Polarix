# Polarix ML Inference Microservice — Integration Guide & API Contract

**Subsystem:** Autonomous Sensor Anomaly Detection & Microgrid Energy Forecasting
**Author:** Person C (Machine Learning Specialist)
**Branch:** `Rex` (**Authoritative Source of Truth for all ML Models & Services**)
**Service Version:** `1.0.0`
**API Version:** `v1`
**Contract Version:** `ml-service-contract-v1`
**Machine-Readable Contract:** `ml/service/results/ml_service_api_contract.json`

---

## 1. Architecture & Authority Declaration

The Polarix ML Service is an independent, production-oriented FastAPI service exposing HTTP/JSON endpoints for Sensor ML anomaly classification and Energy ML load/deficit-risk forecasting.

```text
Physical SCADA / Telemetry Stream
                 ↓
      Person A Backend (Parthi)
                 ↓  HTTP / JSON
      Person C ML Service (Rex)
                 ├── GET  /api/v1/ml/health
                 ├── GET  /api/v1/ml/version
                 ├── POST /api/v1/ml/sensor/analyze
                 └── POST /api/v1/ml/energy/predict
                 ↓  Authoritative ML Responses
      Person A Backend Operational Rules Engine
                 ↓
Alerts / Commands / Resource Scheduling / WebSockets
                 ↓
      Person B Frontend / Digital Twin Dashboard
```

> [!IMPORTANT]
> **AUTHORITY & BOUNDARY INVARIANTS:**
> 1. **Person C ML Service is the sole authority for ML inference.** It encapsulates feature engineering, scalers, PyTorch/Scikit-learn models, reconstruction thresholds, and deficit-risk decision logic ($\tau = 0.35$).
> 2. **Person A's backend consumes the service contract.** The backend is responsible for network transport, persistence, operational dispatch, and frontend delivery. The backend must NOT duplicate ML algorithms or threshold anomaly scores independently.
> 3. **Person B's frontend renders the Digital Twin and displays ML predictions.**

---

## 2. Local Execution

Run the ML service locally from the repository root:

```bash
# Start ML microservice on port 8000
.venv/bin/uvicorn ml.service.app:app --host 0.0.0.0 --port 8000 --reload
```

Interactive documentation:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 3. Endpoints Overview

| Method | Path | Purpose | Stateful | Success Code |
|:---|:---|:---|:---:|:---:|
| `GET` | `/api/v1/ml/health` | Process liveness check | No | `200 OK` |
| `GET` | `/api/v1/ml/version` | Active model versions, thresholds, and metadata | No | `200 OK` |
| `POST` | `/api/v1/ml/sensor/analyze` | Single-point multivariate LSTM anomaly detection | Yes (30-step buffer/sensor) | `200 OK` |
| `POST` | `/api/v1/ml/energy/predict` | Hourly microgrid forecasting & deficit risk | Yes (24-hour buffer/station) | `200 OK` |

---

## 4. Sensor ML API Contract (`POST /api/v1/ml/sensor/analyze`)

### Request Specification:
```json
{
  "timestamp": "2026-09-18T12:00:00Z",
  "station_id": "MTR",
  "sensor_id": "TEMP_001",
  "value": -15.42,
  "quality": "GOOD",
  "unit": "C",
  "source": "SIMULATOR"
}
```

- **Required Fields:** `timestamp`, `station_id` (`"MTR"` or `"BRT"`), `sensor_id`, `value`.
- **Optional Fields:** `quality` (`"GOOD"`, `"MISSING"`, `"DEGRADED"`), `unit`, `source`.

### Response Specification:
```json
{
  "station_id": "MTR",
  "sensor_id": "TEMP_001",
  "timestamp": "2026-09-18T12:00:00Z",
  "value": -15.42,
  "unit": "C",
  "quality": "GOOD",
  "source": "SIMULATOR",
  "anomaly_score": 0.00412,
  "anomaly_status": "NORMAL",
  "anomaly_type": "NORMAL",
  "model_version": "lstm-ae-v1"
}
```

### Sensor ML Semantic Values:
- **`anomaly_status`:** `NORMAL` | `ANOMALY` | `INSUFFICIENT_DATA` (warmup steps 1..29) | `MISSING_DATA` (non-GOOD quality).
- **`anomaly_type`:** `NORMAL` | `SPIKE` | `DRIFT` | `STUCK_VALUE` | `STEP_CHANGE` | `UNKNOWN` | `MISSING_DATA`.
- **Ownership Rule:** Sensor ML models own classification. Backend must NOT re-threshold `anomaly_score`.

---

## 5. Energy ML API Contract (`POST /api/v1/ml/energy/predict`)

### Request Specification:
```json
{
  "timestamp": "2026-09-18T23:00:00Z",
  "station_id": "MTR",
  "power_demand_kw": 48.75,
  "generator_output_kw": 54.20,
  "battery_soc_percent": 82.50,
  "battery_charge_kw": 5.45,
  "battery_discharge_kw": 0.0,
  "fuel_consumption_l": 15.12,
  "temperature_c": -18.35,
  "humidity_percent": 58.40,
  "pressure_hpa": 987.60,
  "wind_speed_mps": 9.20,
  "sensor_anomaly_score": 0.8521,
  "sensor_anomaly_status": "NORMAL",
  "sensor_anomaly_type": "NORMAL",
  "data_quality": "GOOD",
  "source": "SIMULATOR"
}
```

- **Required Physical Fields (12):** `timestamp`, `station_id`, `power_demand_kw`, `generator_output_kw`, `battery_soc_percent`, `battery_charge_kw`, `battery_discharge_kw`, `fuel_consumption_l`, `temperature_c`, `humidity_percent`, `pressure_hpa`, `wind_speed_mps`.
- **Optional Context Fields (5):** `sensor_anomaly_score`, `sensor_anomaly_status`, `sensor_anomaly_type`, `data_quality`, `source`.

### Stateful 24-Hour Buffering Responses:

#### A. Warmup / After Timeline Gap ($N < 24$ hours):
```json
{
  "status": "INSUFFICIENT_HISTORY",
  "station_id": "MTR",
  "latest_timestamp": "2026-09-18T05:00:00Z",
  "available_history": 6,
  "required_history": 24,
  "prediction": null,
  "message": "Buffering in progress: 6/24 contiguous hourly records."
}
```

#### B. Prediction Available ($N \ge 24$ contiguous hours):
```json
{
  "status": "PREDICTION_AVAILABLE",
  "station_id": "MTR",
  "latest_timestamp": "2026-09-18T23:00:00Z",
  "available_history": 24,
  "required_history": 24,
  "prediction": {
    "station_id": "MTR",
    "timestamp": "2026-09-18T23:00:00Z",
    "contract_version": "energy-ml-contract-v1",
    "model_version": "energy-ml-v1-candidate",
    "forecast_model_version": "lstm-energy-baseline-v1",
    "risk_model_version": "energy-deficit-risk-v1",
    "forecasts": {
      "power_demand_1h_kw": 49.82,
      "battery_soc_1h_percent": 81.65,
      "energy_demand_6h_kwh": 302.40,
      "energy_demand_24h_kwh": 1225.80
    },
    "deficit_risk": {
      "probability": 0.0075,
      "decision": false,
      "threshold": 0.35
    },
    "provenance": {
      "source": "SYNTHETIC_POLARIX_OPERATIONAL_DATA",
      "model_status": "CANDIDATE",
      "calibration_reference": "Australian Antarctic Data Centre (AADC CC BY 4.0) & NCPOR Meteorological Archives",
      "disclaimer": "Validated on synthetic Polarix operational microgrid telemetry. Not validated on real classified station SCADA telemetry."
    }
  },
  "message": "Unified energy prediction successfully generated."
}
```

---

## 6. Station Identifiers & Gateway Normalization (`BHR` $\to$ `BRT`)

- **Canonical Station Codes:** `MTR` (Maitri), `BRT` (Bharati).
- **`BHR` Rejection:** Any request with `station_id: "BHR"` returns **HTTP 400 Bad Request**.
- **Normalization Ownership:** Person A's backend gateway must map `"BHR"` to `"BRT"` before sending requests to the ML service.

---

## 7. Error Semantics Matrix

| HTTP Status | Condition | Example Detail Message | Backend Action |
|:---|:---|:---|:---|
| **400 Bad Request** | Legacy `station_id: "BHR"` | `"Invalid station_id 'BHR'. Person C ML contracts enforce 'BRT'..."` | Normalize `"BHR"` to `"BRT"` |
| **400 Bad Request** | Duplicate timestamp | `"Duplicate timestamp '...' received for sensor..."` | Skip duplicate transmission |
| **400 Bad Request** | Out-of-order timestamp | `"Out-of-order telemetry timestamp '...'..."` | Discard or queue for historical batch |
| **400 Bad Request** | NaN or Infinite float | `"Field 'power_demand_kw' contains NaN or infinite value."` | Reject bad telemetry packet |
| **422 Unprocessable** | Missing required physical field | `[{"loc": ["body", "power_demand_kw"], "msg": "Field required"}]` | Fix payload schema |
| **500 Server Error** | Unexpected compute exception | `"Energy ML inference error: <msg>"` | Log alert; report issue to Person C |

---

## 8. Provenance & Synthetic Data Limitation

> [!CAUTION]
> **DATA PROVENANCE NOTICE:**
> Real sub-hourly operational microgrid telemetry for Maitri and Bharati stations is classified infrastructure data and is not publicly distributed. All Energy ML models were trained and validated on high-fidelity synthetic operational telemetry (`SYNTHETIC_POLARIX_OPERATIONAL_DATA`) calibrated against open-access NCPOR weather envelopes and Australian Antarctic Division (AADC CC BY 4.0) historical seasonal load profiles. Model status is `CANDIDATE`.

---

## 9. Example cURL Invocations

### Health Check:
```bash
curl -X GET http://localhost:8000/api/v1/ml/health
```

### Version Metadata:
```bash
curl -X GET http://localhost:8000/api/v1/ml/version
```

### Sensor Analysis:
```bash
curl -X POST http://localhost:8000/api/v1/ml/sensor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-09-18T12:00:00Z",
    "station_id": "MTR",
    "sensor_id": "TEMP_001",
    "value": -15.42,
    "quality": "GOOD",
    "unit": "C",
    "source": "SIMULATOR"
  }'
```

### Energy Prediction:
```bash
curl -X POST http://localhost:8000/api/v1/ml/energy/predict \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-09-18T23:00:00Z",
    "station_id": "MTR",
    "power_demand_kw": 48.75,
    "generator_output_kw": 54.20,
    "battery_soc_percent": 82.50,
    "battery_charge_kw": 5.45,
    "battery_discharge_kw": 0.0,
    "fuel_consumption_l": 15.12,
    "temperature_c": -18.35,
    "humidity_percent": 58.40,
    "pressure_hpa": 987.60,
    "wind_speed_mps": 9.20,
    "sensor_anomaly_score": 0.8521,
    "sensor_anomaly_status": "NORMAL",
    "sensor_anomaly_type": "NORMAL",
    "data_quality": "GOOD",
    "source": "SIMULATOR"
  }'
```
