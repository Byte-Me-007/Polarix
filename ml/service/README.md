# Polarix ML Inference Microservice

**Subsystem:** Autonomous Sensor Anomaly Detection & Microgrid Energy Forecasting
**Author:** Person C (Machine Learning Specialist)
**Branch:** `Rex` (**Source of Truth for all ML Models & Services**)
**Service Version:** `1.0.0`
**FastAPI Service Location:** `ml/service/`

---

## 1. Service Purpose & Architectural Role

The Polarix ML service is an independent, production-oriented FastAPI microservice exposing HTTP/JSON boundaries for:
1. **Sensor ML Anomaly Detection:** Real-time multivariate LSTM-Autoencoder anomaly scoring and classification (`SPIKE`, `DRIFT`, `STUCK_VALUE`, `STEP_CHANGE`, etc.) for Maitri (`MTR`) and Bharati (`BRT`).
2. **Energy ML Forecasting & Deficit Risk:** Real-time multi-horizon load forecasting (1h, 6h, 24h), battery state-of-charge trajectory planning (1h), and binary energy deficit risk classification ($\tau = 0.35$).

```text
Simulator / Physical Telemetry Stream
                 ↓
      Person A Backend (Parthi)
                 ↓  HTTP/JSON
      Person C ML Service (Rex)
                 ├── GET  /api/v1/ml/health
                 ├── GET  /api/v1/ml/version
                 ├── POST /api/v1/ml/sensor/analyze
                 └── POST /api/v1/ml/energy/predict
                 ↓  Unified ML Response
      Person A Backend Operational Rules Engine
                 ↓
Alerts / Commands / Resource Scheduling / WebSockets
                 ↓
      Person B Frontend / Digital Twin Dashboard
```

> [!IMPORTANT]
> **SOURCE OF TRUTH DECLARATION:**
> Branch `Rex` is the authoritative source of truth for all ML implementations, trained model weights, feature scalers, decision thresholds, and inference contracts. Person A's backend consumes this HTTP service interface and must not reproduce or rewrite ML logic.

---

## 2. Local Execution

Run the ML service locally using Uvicorn:

```bash
# From repository root
.venv/bin/uvicorn ml.service.app:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI documentation is automatically served at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 3. API Endpoints

### A. `GET /api/v1/ml/health`
Determines service liveness and operational readiness.

**Response (200 OK):**
```json
{
  "status": "ok",
  "service": "polarix-ml"
}
```

---

### B. `GET /api/v1/ml/version`
Exposes release metadata, component model versions, frozen thresholds, and provenance context.

**Response (200 OK):**
```json
{
  "service_name": "polarix-ml-service",
  "service_version": "1.0.0",
  "contract_version": "energy-ml-contract-v1",
  "sensor_models": {
    "maitri": {
      "model_version": "lstm-ae-v1",
      "station_id": "MTR",
      "model_type": "LSTM Autoencoder",
      "frozen_threshold": 0.017674,
      "sequence_length": 30,
      "status": "PRODUCTION"
    },
    "bharati": {
      "model_version": "lstm-ae-bharati-v1",
      "station_id": "BRT",
      "model_type": "LSTM Autoencoder",
      "frozen_threshold": 0.013215307652775843,
      "sequence_length": 30,
      "status": "PRODUCTION"
    }
  },
  "energy_models": {
    "unified_model_version": "energy-ml-v1-candidate",
    "model_status": "CANDIDATE",
    "forecast_model_version": "lstm-energy-baseline-v1",
    "risk_model_version": "energy-deficit-risk-v1",
    "deficit_risk_threshold": 0.35,
    "required_history_hours": 24,
    "supported_stations": ["MTR", "BRT"]
  },
  "provenance": {
    "source": "SYNTHETIC_POLARIX_OPERATIONAL_DATA",
    "calibration_references": [
      "National Centre for Polar and Ocean Research (NCPOR) Meteorological Archives",
      "Australian Antarctic Data Centre (AADC CC BY 4.0) Electrical Load Archives"
    ],
    "disclaimer": "Validated on synthetic Polarix operational microgrid telemetry. Not validated on real classified station SCADA telemetry."
  }
}
```

---

### C. `POST /api/v1/ml/sensor/analyze`
Executes LSTM-Autoencoder sensor anomaly detection for a single incoming observation.

**Request Payload:**
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

**Response (200 OK):**
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

- **Warmup Behavior:** Observations 1 through 29 return `anomaly_status: "INSUFFICIENT_DATA"` with `anomaly_score: null`.
- **Steady State:** Observation 30+ emits scored reconstruction error and classification (`NORMAL` vs `ANOMALY` / `SPIKE` / `DRIFT` / `STUCK_VALUE`).
- **Missing Quality:** Packets with `quality: "MISSING"` trigger `anomaly_status: "MISSING_DATA"` and safely flush sensor history to prevent contamination.

---

### D. `POST /api/v1/ml/energy/predict`
Ingests a single hourly microgrid telemetry record and generates multi-horizon forecasts and deficit risk alarms.

**Request Payload:**
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

**Response (200 OK — Warmup / Gap: $N < 24$ hours):**
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

**Response (200 OK — Contiguous $\ge 24$ hours):**
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

## 4. Station Identifiers & Gateway Normalization

The ML service strictly accepts only two canonical station codes:
- `MTR` — Maitri Station
- `BRT` — Bharati Station

### Legacy Station Code Rejection:
Any request containing `station_id: "BHR"` is deterministically rejected with **HTTP 400 Bad Request**. Person A's backend gateway must map `"BHR"` to `"BRT"` prior to dispatching HTTP requests to the ML service. Zero silent aliasing is performed.

---

## 5. Error Semantics

| HTTP Status | Trigger Condition | Response Structure |
|:---|:---|:---|
| **400 Bad Request** | Legacy `station_id: "BHR"`, duplicate timestamp, out-of-order timestamp, unsupported station code, or physical value NaN/Inf. | `{"detail": "<descriptive_error_explanation>"}` |
| **422 Unprocessable Entity** | Missing required physical schema fields or invalid data types. | FastAPI standard Pydantic validation error array. |
| **500 Internal Server Error** | Unexpected PyTorch/Scikit-learn compute failure. | `{"detail": "Energy ML inference error: <msg>"}` |

---

## 6. Provenance & Synthetic Data Disclaimer

> [!CAUTION]
> **DATA PROVENANCE STATEMENT:**
> Operational microgrid telemetry for Maitri and Bharati stations is classified infrastructure data and is not publicly released. All Energy ML models were trained, evaluated, and hardened on high-fidelity synthetic operational telemetry (`SYNTHETIC_POLARIX_OPERATIONAL_DATA`) conditioned on empirical Antarctic meteorological distributions. Model status remains `CANDIDATE`.
