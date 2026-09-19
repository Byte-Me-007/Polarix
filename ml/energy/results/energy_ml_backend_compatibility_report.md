# Energy ML & Backend Telemetry Compatibility Audit Report (Step 08)

**Project:** Polarix — Smart India Hackathon 2026 (Problem Statement SIH26060, Team Byte Me_26 / 143760)
**Subsystem:** Energy Forecasting & Microgrid Optimization
**Author:** Person C — Machine Learning Specialist
**Audited Components:** `EnergyMLService`, `EnergyForecaster`, `DeficitRiskForecaster`, `energy_ml_inference_contract.json` vs Person A Backend Telemetry Architecture
**Audit Status:** `ML_CONTRACT_VERIFIED__STATION_ID_ALIGNMENT_REQUIRED`
**Date (UTC):** 2026-09-19

---

## 1. Executive Summary

This audit establishes the formal interface and compatibility boundary between Person C's **Energy ML subsystem** (`ml/energy/`) and Person A's **backend telemetry ingestion architecture**.

### Key Audit Conclusions:
1. **Zero Lookahead Leakage:** All 18 input features for the multi-task `EnergyLSTM` baseline and all 26 features for the `HistGradientBoosting` Deficit-Risk classifier can be **100% causally derived** from 12 canonical raw physical telemetry fields. Person A's backend **never** needs to compute or send precomputed rolling averages, trigonometric cycles, or ratios.
2. **Unified Contract Established:** The unified orchestrator `EnergyMLService` (`ml/energy/inference/energy_ml_service.py`) encapsulates both models and exposes a single canonical prediction entrypoint returning multi-horizon load forecasts ($t+1\,\text{h}, t+6\,\text{h}, t+24\,\text{h}$), battery SoC ($t+1\,\text{h}$), and binary deficit-risk early warning ($\tau = 0.3500$).
3. **Primary Actionable Mismatch (Station ID):** Person C ML operates strictly on canonical station identifiers **`MTR` (Maitri)** and **`BRT` (Bharati)**. Person A backend contains legacy/transitional references to **`BHR`**. Person A must standardize backend ingestion to canonical **`BRT`** before integrated execution. Person C ML does **not** introduce a silent alias, ensuring unverified station strings are rejected loudly.
4. **Historical Lookback Requirement:** Unified inference requires a continuous sliding window of **24 hourly records** ($\ge 24\,\text{h}$). Insufficient history is rejected with a descriptive `ValueError`.

---

## 2. Current Energy ML Contract Overview

The authoritative unified output structure (`energy-ml-contract-v1`, status `CANDIDATE`) is defined in `ml/energy/results/energy_ml_inference_contract.json`:

```json
{
  "station_id": "MTR",
  "timestamp": "2026-09-18T10:00:00Z",
  "contract_version": "energy-ml-contract-v1",
  "model_version": "energy-ml-v1-candidate",
  "forecast_model_version": "lstm-energy-baseline-v1",
  "risk_model_version": "energy-deficit-risk-v1",
  "forecasts": {
    "power_demand_1h_kw": 48.52,
    "battery_soc_1h_percent": 82.35,
    "energy_demand_6h_kwh": 298.10,
    "energy_demand_24h_kwh": 1210.45
  },
  "deficit_risk": {
    "probability": 0.0084,
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

---

## 3. Backend Telemetry Architecture Observed

Person A's backend architecture exhibits two developmental tiers:

1. **Canonical Direction (Modern / Production Target):**
   - Entities: `Station`, `Sensor`, `Telemetry`
   - Ingestion Route: `/telemetry/`
   - Real-Time Protocol: MQTT station telemetry topics $\to$ backend event bus $\to$ WebSocket client fanout.
   - Design: Flat time-series records containing structured physical measurements and metadata.
2. **Legacy / Transitional Direction (Early Scaffold):**
   - Entities: `Device`, `SensorReading`
   - Ingestion Route: `/sensor-readings/`
   - Design: Key-value sensor readings without multi-field microgrid state vectors.

> [!NOTE]
> **Compatibility Decision:** Person C Energy ML integrates exclusively with Person A's **Canonical Telemetry Direction** (`/telemetry/`, MQTT `polarix/{station_id}/telemetry`). The legacy architecture remains untouched.

---

## 4. Field-by-Field Compatibility Matrix

| # | Field Name | Requirement | Data Type | Physical Unit | Range / Bounds | Status | Person A Action |
|:---|:---|:---|:---|:---|:---|:---|:---|
| 1 | `timestamp` | **REQUIRED** | ISO-8601 String | UTC | Valid ISO String | `COMPATIBLE` | Send standard ISO-8601 UTC timestamp. |
| 2 | `station_id` | **REQUIRED** | String Enum | Code | `MTR`, `BRT` | `ATTENTION` | Standardize Bharati to `BRT` (resolve `BHR`). |
| 3 | `power_demand_kw` | **REQUIRED** | Float | kW | $[0.0, 300.0]$ | `COMPATIBLE` | Send total station electrical + thermal load. |
| 4 | `generator_output_kw`| **REQUIRED** | Float | kW | $[0.0, 300.0]$ | `COMPATIBLE` | Send active generator electrical output. |
| 5 | `battery_soc_percent`| **REQUIRED** | Float | % | $[0.0, 100.0]$ | `COMPATIBLE` | Send BESS State-of-Charge percentage. |
| 6 | `battery_charge_kw` | **REQUIRED** | Float | kW | $[0.0, 100.0]$ | `COMPATIBLE` | Send BESS charging power (non-negative). |
| 7 | `battery_discharge_kw`| **REQUIRED**| Float | kW | $[0.0, 100.0]$ | `COMPATIBLE` | Send BESS discharging power (non-negative). |
| 8 | `fuel_consumption_l` | **REQUIRED** | Float | L/h | $[0.0, 100.0]$ | `COMPATIBLE` | Send hourly diesel fuel burn rate. |
| 9 | `temperature_c` | **REQUIRED** | Float | °C | $[-65.0, 25.0]$ | `COMPATIBLE` | Send ambient outdoor air temperature. |
| 10| `humidity_percent` | **REQUIRED** | Float | % | $[0.0, 100.0]$ | `COMPATIBLE` | Send ambient relative humidity. |
| 11| `pressure_hpa` | **REQUIRED** | Float | hPa | $[850.0, 1100.0]$ | `COMPATIBLE` | Send barometric surface air pressure. |
| 12| `wind_speed_mps` | **REQUIRED** | Float | m/s | $[0.0, 80.0]$ | `COMPATIBLE` | Send sustained wind speed. |
| 13| *`sensor_anomaly_score`*| OPTIONAL | Float | z-score | $[0.0, 500.0]$ | `COMPATIBLE` | Pass if upstream Sensor ML is active; defaults to 1.0. |
| 14| *`sensor_anomaly_status`*| OPTIONAL | String Enum | - | `NORMAL`, `ANOMALY` | `COMPATIBLE` | Pass if available; defaults to `NORMAL`. |
| 15| *`data_quality`* | OPTIONAL | String Enum | - | `GOOD`, `MISSING` | `COMPATIBLE` | Pass if known; defaults to `GOOD`. |

---

## 5. Station ID Investigation & Discrepancy Analysis

### Findings:
- **Person C Machine Learning Canonical Identifiers:**
  - `MTR`: Maitri Station (Schirmacher Oasis, 120 kW rated generator).
  - `BRT`: Bharati Station (Larsemann Hills, 150 kW rated generator).
  - Used consistently across all dataset schemas, synthetic generators, LSTM scalers, feature encoders (`station_is_brt`), model configs, and unit tests.
- **Person A Backend References:**
  - `MTR`: Used consistently.
  - `BHR`: Found in some backend routes/models as an alternate abbreviation for Bharati.

### Resolution Policy:
- Person C ML **rejects** `station_id == "BHR"` with `ValueError("Invalid station_id encountered: {'BHR'}. Expected 'MTR' or 'BRT'")`.
- Person C will **NOT** silently alias `BHR -> BRT` in ML code. Silent aliasing creates hidden data corruption and bypasses contract validation.
- **Action Required for Person A:** In the upcoming backend integration milestone, standardize backend station codes to `BRT` or establish an explicit gateway normalization layer before calling `EnergyMLService`.

---

## 6. Timestamp, Window & Forecast Horizon Audit

1. **Timezone & Cadence:**
   - All timestamps must be in **UTC** (ISO-8601 string, e.g. `2026-09-18T10:00:00Z`).
   - Expected cadence is **1-hour (hourly)** intervals.
2. **Historical Lookback:**
   - The neural forecasting model (`EnergyLSTM`) operates on a fixed lookback window of **24 hours** ($t-23 \dots t$).
   - `EnergyMLService.predict()` strictly requires $\ge 24$ contiguous historical records.
3. **Forecast Horizons (Causal Multi-Horizon):**
   - $P_{\text{demand}}(t+1\,\text{h})$: Instantaneous power demand 1 hour ahead in kW.
   - $\text{SoC}(t+1\,\text{h})$: Battery State-of-Charge 1 hour ahead in %.
   - $E_{\text{demand}}(t+1..t+6\,\text{h})$: Cumulative energy consumption over the next 6 hours in kWh (used for diesel generator dispatch scheduling).
   - $E_{\text{demand}}(t+1..t+24\,\text{h})$: Cumulative energy consumption over the next 24 hours in kWh (used for day-ahead fuel and budget planning).
   - $\text{Deficit Risk}(t \to t+1\,\text{h})$: Probability of battery SoC dropping below 25% or demand exceeding 95% rated generator power within the next hour.
4. **Anti-Leakage Verification:**
   - No prediction horizon derivation references future targets during inference.
   - Mutation of timestamps $> t$ has zero mathematical effect on predictions at $t$.

---

## 7. Upstream Sensor ML Anomaly Feature Integration

1. **Ownership Authority:** Person C Sensor ML (`ml/inference/maitri_ml_service.py`, `ml/inference/bharati_ml_service.py`) is the **sole authority** on sensor health, anomaly scores, and classification states (`SPIKE`, `DRIFT`, `STUCK_VALUE`, `MISSING_DATA`). Person A backend must **not** independently re-threshold or recalculate anomaly status.
2. **Energy ML Consumption:**
   - `sensor_anomaly_score`: Continuous composite reconstruction error z-score (defaults to 1.0 if omitted).
   - `sensor_anomaly_status`: Health state (`ANOMALY` $\to$ `sensor_is_anomaly=1.0`, otherwise 0.0).
   - `data_quality`: Telemetry acquisition state (`MISSING` $\to$ `sensor_is_missing=1.0`).
3. **Graceful Fallback:** If Sensor ML has not yet processed a telemetry batch, Energy ML operates reliably using nominal defaults (`score=1.0, status="NORMAL", quality="GOOD"`).

---

## 8. MQTT & WebSocket Compatibility Blueprint

### A. MQTT Ingestion Flow (Simulator $\to$ Backend $\to$ Energy ML):
- **Topic Convention:** `polarix/telemetry/{station_id}` (e.g. `polarix/telemetry/MTR`, `polarix/telemetry/BRT`).
- **Payload:** JSON payload containing the 12 required fields defined in Section 4.
- **Buffer Management:** Person A backend maintains an in-memory sliding ring buffer of the latest 24 hourly readings per station (`deque(maxlen=24)`).

### B. WebSocket Dispatch Flow (Backend $\to$ Frontend Digital Twin):
- **Topic / Event:** `energy_forecast_update`
- **Payload:** Serialized dictionary from `UnifiedEnergyPrediction.to_dict()`.
- **Frontend Consumption:** Person B's 3D Digital Twin and dashboard components consume the disaggregated `forecasts` object (multi-horizon energy curves) and `deficit_risk` object (amber/red alarm state) directly.

---

## 9. Derived-Feature Causality Proofs

All derived features used by the models are proven to be strictly causal (zero lookahead leakage):

| Feature Name | Used By | Exact Mathematical Formula | Required History | Lookahead Free? |
|:---|:---|:---|:---|:---:|
| `station_is_brt` | LSTM, Risk | `1.0 if station_id == 'BRT' else 0.0` | 1 record ($t$) | **YES** |
| `sin_hour`, `cos_hour` | LSTM, Risk | $\sin, \cos\left(2\pi \cdot \text{hour}(t) / 24.0\right)$ | 1 record ($t$) | **YES** |
| `sin_day`, `cos_day` | LSTM, Risk | $\sin, \cos\left(2\pi \cdot \text{dayofyear}(t) / 365.25\right)$ | 1 record ($t$) | **YES** |
| `generator_utilization`| Risk | $\text{clip}(P_{\text{gen}}(t) / P_{\text{rated}}, 0.0, 2.0)$ | 1 record ($t$) | **YES** |
| `demand_to_gen_ratio` | Risk | $\text{clip}(P_{\text{demand}}(t) / (P_{\text{gen}}(t) + 10^{-4}), 0.0, 5.0)$ | 1 record ($t$) | **YES** |
| `battery_net_power` | Risk | $P_{\text{charge}}(t) - P_{\text{discharge}}(t)$ | 1 record ($t$) | **YES** |
| `thermal_headroom` | Risk | $\max(0.0, 18.0 - T_{\text{ambient}}(t))$ | 1 record ($t$) | **YES** |
| `sensor_is_anomaly` | LSTM, Risk | `1.0 if sensor_status == 'ANOMALY' else 0.0` | 1 record ($t$) | **YES** |
| `sensor_is_missing` | LSTM, Risk | `1.0 if sensor_status == 'MISSING_DATA' or quality == 'MISSING' else 0.0` | 1 record ($t$) | **YES** |
| `recent_demand_mean_6h`| Risk | $\frac{1}{K}\sum_{i=0}^{K-1} P_{\text{demand}}(t-i)$ with $K = \min(N, 6)$ | $[t-5, t]$ | **YES** |
| `recent_demand_slope_3h`| Risk | $\frac{P_{\text{demand}}(t) - P_{\text{demand}}(t-3)}{3.0}$ (or 0.0 if $N < 3$) | $t, t-3$ | **YES** |
| `recent_soc_mean_6h` | Risk | $\frac{1}{K}\sum_{i=0}^{K-1} \text{SoC}(t-i)$ with $K = \min(N, 6)$ | $[t-5, t]$ | **YES** |
| `recent_soc_slope_3h` | Risk | $\frac{\text{SoC}(t) - \text{SoC}(t-3)}{3.0}$ (or 0.0 if $N < 3$) | $t, t-3$ | **YES** |

---

## 10. Blocking Issues (Must Be Addressed for Integration)

1. **[BLK-01] Station Identifier Alignment:**
   - **Problem:** Person A backend uses `BHR` in select routes/enums, while Person C ML strictly requires `BRT`.
   - **Resolution:** Person A must standardize station codes to `BRT` in backend telemetry models and MQTT topics prior to integration.

---

## 11. Non-Blocking Issues (Operational Considerations)

1. **[NONBLK-01] Cold-Start 24-Hour Buffer Accumulation:**
   - On initial simulator or service startup, the backend must accumulate 24 hourly records before calling `EnergyMLService.predict()`. For single-record streaming prior to 24h, the standalone `DeficitRiskForecaster.predict_dict()` may optionally be called.
2. **[NONBLK-02] Sensor ML Upstream Coupling:**
   - If upstream Sensor ML has not yet processed a record, Energy ML safely defaults to nominal values (`score=1.0, status='NORMAL'`).

---

## 12. Exact Person A Backend Changes Required Later (In Integration Step)

When Person A begins backend integration:
1. **Model & Topic Naming:** Use `MTR` and `BRT` as the authoritative station IDs across all Pydantic models, SQLite schemas, and MQTT topics (`polarix/telemetry/MTR`, `polarix/telemetry/BRT`).
2. **Ring Buffer Service:** Implement a rolling buffer of 24 hourly telemetry readings per station (`deque(maxlen=24)`).
3. **Energy ML Invocation:**
   ```python
   from ml.energy.inference.energy_ml_service import EnergyMLService

   energy_service = EnergyMLService()
   prediction = energy_service.predict(station_24h_dataframe)
   response_payload = prediction.to_dict()
   ```
4. **WebSocket Fanout:** Broadcast `response_payload` to connected frontend clients under event type `energy_forecast_update`.

---

## 13. What Should NOT Be Changed

1. **Do NOT modify Sensor ML files:** Frozen models (`lstm-ae-v1.pt`, `lstm-ae-bharati-v1.pt`) and thresholds must remain untouched.
2. **Do NOT alter Energy LSTM architecture or weights:** `energy_lstm_baseline.pt` and scalers are frozen.
3. **Do NOT change the Deficit-Risk threshold:** $\tau = 0.3500$ is fixed and validated.
4. **Do NOT precompute derived features in the backend:** Person A sends raw physical telemetry; ML derives all features causally.
5. **Do NOT invent a fake `BHR -> BRT` alias inside ML:** Station codes must remain strict and verified.

---

## 14. Recommended Next Integration Step

Once Person A aligns the backend station codes (`BHR` $\to$ `BRT`) and implements the 24-hour ring buffer, proceed to:
- **Energy Step 09:** Formal Person A Backend Service Integration & End-to-End Ingestion Smoke Testing.
