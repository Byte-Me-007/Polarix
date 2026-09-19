# Polarix Energy ML — Backend Integration Handoff Document

**Target Audience:** Person A (Backend Engineer)  
**Author:** Person C (Machine Learning Specialist)  
**Subsystem:** Energy Forecasting & Microgrid Optimization Subsystem  
**Reference Milestone Commit:** `247beea` (`feat(ml): establish energy forecasting and deficit risk integration milestone`)  
**Date:** 2026-09-19  

---

## 1. Integration Status

- **ML Subsystem Status:** `VALIDATED_ML_MILESTONE`
- **Adapter Validation:** The ML boundary adapter (`EnergyMLBackendAdapter`) is fully implemented and tested (15/15 E2E integration tests passing).
- **Backend Integration Status:** `ML_SIDE_READY_BACKEND_PENDING` (Actual backend service integration has not yet been executed in Person A codebase).
- **Model Status:** `CANDIDATE` (Validated strictly against synthetic Polarix operational microgrid telemetry; not on classified real station SCADA records).

---

## 2. Canonical Station Identifiers & Station Code Normalization

The Energy ML subsystem strictly accepts only two canonical station codes:
- `MTR` — Maitri Station (Inland Oasis, Queen Maud Land)
- `BRT` — Bharati Station (Coastal Promontory, Larsemann Hills)

### Critical Requirement for Person A:
- **`BHR` Rejection:** Any telemetry containing `station_id: "BHR"` will raise an explicit `ValueError` from the ML adapter.
- **Normalization Ownership:** Person A's backend gateway/ingestion layer **must normalize** legacy `"BHR"` representations to canonical `"BRT"` prior to invoking the ML adapter. The ML adapter intentionally performs zero silent aliasing.

---

## 3. Canonical Telemetry Input Contract

Person A's streaming telemetry ingestion pipeline should feed raw physical dictionaries directly into the adapter.

### Required Fields (Physical Measurements):
```json
{
  "timestamp": "2026-09-18T12:00:00Z",
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
  "wind_speed_mps": 9.20
}
```

### Optional Context Fields:
```json
{
  "sensor_anomaly_score": 0.8521,
  "sensor_anomaly_status": "NORMAL",
  "sensor_anomaly_type": "NORMAL",
  "data_quality": "GOOD",
  "source": "SIMULATOR"
}
```

### Constraints & Anti-Leakage Boundary Rules:
- **Do NOT send target columns** (no `target_*` or future values).
- **Do NOT send ML-engineered features** (no rolling averages, lag features, or sin/cos encodings). The adapter computes these internally.
- **Do NOT calculate rolling features in the backend.**
- **Do NOT independently classify sensor anomalies.** Sensor ML flags are ingested purely as contextual metadata.

---

## 4. Adapter Entry Point & Streaming API

The primary entry point is `EnergyMLBackendAdapter` in `ml/energy/inference/backend_adapter.py`.

### Instantiation & Ingestion:
```python
from pathlib import Path
from ml.energy.inference.backend_adapter import EnergyMLBackendAdapter

# Instantiate once at backend startup
adapter = EnergyMLBackendAdapter(model_dir=Path("ml/energy/models"))

# Call per incoming hourly telemetry record
response = adapter.ingest_and_predict(telemetry_dict)
```

### Buffering & Streaming Behavior:
1. **Startup / Cold-Start:**
   - Hours 1 through 23 return `response.status == "INSUFFICIENT_HISTORY"` with `response.prediction == None` and `response.available_history == N`.
   - Exactly on the 24th contiguous hourly record, the adapter returns `response.status == "PREDICTION_AVAILABLE"` with the full unified prediction.
2. **Rolling Window:**
   - Every subsequent continuous hourly record ($t \ge 24$) generates a rolling prediction over the latest contiguous $[t-23, t]$ window.
3. **Timeline Gap Handling:**
   - If a gap $> 1\,\text{h}$ occurs (e.g., telemetry drop or blackout), the adapter resets the contiguous window count and returns `INSUFFICIENT_HISTORY` until 24 new contiguous hourly records arrive. No synthetic observations are fabricated across gaps.
4. **Validation Rejections:**
   - Out-of-order timestamps or duplicate timestamps raise deterministic `ValueError` exceptions without corrupting the existing station buffer.

---

## 5. Output Payload Contract (`energy-ml-contract-v1`)

When `response.status == "PREDICTION_AVAILABLE"`, `response.prediction` (or `response.to_dict()["prediction"]`) conforms strictly to `energy-ml-contract-v1`:

```json
{
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
}
```

- **Forecasting Targets:**
  - `power_demand_1h_kw`: 1-hour ahead predicted electrical demand (kW).
  - `battery_soc_1h_percent`: 1-hour ahead predicted BESS state of charge (%).
  - `energy_demand_6h_kwh`: 6-hour cumulative energy demand for generator staging (kWh).
  - `energy_demand_24h_kwh`: 24-hour cumulative energy demand for day-ahead dispatch (kWh).
- **Deficit Risk Alarm:**
  - `probability`: Model probability of impending deficit event ($\text{SoC} < 25\%$ or demand $> 95\%$ rated capacity).
  - `decision`: Binary alarm flag (`true` if probability $\ge 0.35$, `false` otherwise).
  - `threshold`: Operating decision threshold (`0.35`).

---

## 6. Subsystem Ownership Boundary

| Responsibility Area | Person C (ML Specialist) | Person A (Backend Engineer) | Person B (Frontend Engineer) |
|:---|:---:|:---:|:---:|
| **Model Architectures & Weights** | **Owner** | Consumer | Consumer |
| **Model Feature Engineering** | **Owner** | N/A | N/A |
| **ML Inference & Thresholds** | **Owner** | N/A | N/A |
| **ML Contracts & Adapters** | **Owner** | Consumer | Consumer |
| **Telemetry Ingestion & Gateway** | N/A | **Owner** | N/A |
| **Station Code Normalization (`BHR` $\to$ `BRT`)** | N/A | **Owner** | N/A |
| **Database Persistence & Schemas** | N/A | **Owner** | N/A |
| **Operational Rules & Dispatch Logic**| N/A | **Owner** | N/A |
| **REST & WebSocket API Endpoints** | N/A | **Owner** | Consumer |
| **Digital Twin UI & Visualizations** | N/A | N/A | **Owner** |

---

## 7. Synthetic-Data Limitation & Scientific Provenance

> [!IMPORTANT]
> **SYNTHETIC-DATA DISCLAIMER:**
> 1. Real sub-hourly microgrid telemetry for Maitri and Bharati stations is classified infrastructure data and is not publicly released.
> 2. All Energy ML models were trained and validated on high-fidelity synthetic Polarix operational telemetry (`SYNTHETIC_POLARIX_OPERATIONAL_DATA`) conditioned on empirical Antarctic environmental bounds from NCPOR meteorological archives and Australian Antarctic Division historical load dynamics.
> 3. Models must be labeled as `CANDIDATE` status in operational reporting. Do not claim production accuracy against classified real Indian Antarctic station SCADA records.

---

## 8. Recommended Backend Integration Sequence

```text
Canonical Telemetry Stream
           ↓
Station Normalization (ensure 'BRT' for Bharati)
           ↓
EnergyMLBackendAdapter.ingest_and_predict()
           ↓
24-Hour Contiguous Buffer Check
   ├── INSUFFICIENT_HISTORY → Log status (wait for 24 hours)
   └── PREDICTION_AVAILABLE → Yield Unified Prediction
           ↓
Persist Prediction to Backend Database
           ↓
Backend Operational Rules Engine
   ├── Compare Forecast vs Spinning Reserve
   └── Check deficit_risk.decision == True
           ↓
Alert / Dispatch Command Generation
           ↓
WebSocket / REST Endpoints
           ↓
Person B Frontend / Digital Twin Dashboard
```

---

## 9. Contract & Reference Artifacts

- **Authoritative Inference Contract:** [`ml/energy/results/energy_ml_inference_contract.json`](file:///Users/rexjohnabraham/Documents/Polarix_C/ml/energy/results/energy_ml_inference_contract.json)
- **Authoritative Adapter Contract:** [`ml/energy/results/energy_ml_backend_adapter_contract.json`](file:///Users/rexjohnabraham/Documents/Polarix_C/ml/energy/results/energy_ml_backend_adapter_contract.json)
- **Compatibility Matrix:** [`ml/energy/results/energy_ml_backend_compatibility_matrix.json`](file:///Users/rexjohnabraham/Documents/Polarix_C/ml/energy/results/energy_ml_backend_compatibility_matrix.json)
- **Representative E2E Example:** [`ml/energy/results/energy_ml_backend_e2e_example.json`](file:///Users/rexjohnabraham/Documents/Polarix_C/ml/energy/results/energy_ml_backend_e2e_example.json)
- **Milestone Manifest:** [`ml/energy/results/energy_ml_milestone_manifest.json`](file:///Users/rexjohnabraham/Documents/Polarix_C/ml/energy/results/energy_ml_milestone_manifest.json)
