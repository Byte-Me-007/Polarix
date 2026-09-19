# Polarix Energy Forecasting & Microgrid Optimization Module

**Project:** Polarix — Smart India Hackathon 2026 (Problem Statement SIH26060)
**Team:** Byte Me_26 (Team ID: 143760)
**Author:** Person C — Machine Learning Specialist
**Station Scope:** Maitri (`MTR`) and Bharati (`BRT`)
**Status:** `DEFICIT_RISK_PREDICTION_ESTABLISHED`
**Date:** 2026-09-19

---

## 1. Energy ML Subsystem Purpose & Scope

The Energy ML module provides real-time electrical load forecasting, diesel generator dispatch optimization, Battery Energy Storage System (BESS) State-of-Charge (SoC) trajectory planning, and energy deficit risk early-warning for India's Antarctic research stations:
- **Maitri (`MTR`)**: Inland oasis station (Schirmacher Oasis, 70°46′S, 11°44′E) with high heating demand, diesel generation, and strong seasonal thermal swings.
- **Bharati (`BRT`)**: Coastal promontory station (Larsemann Hills, 69°24′S, 76°11′E) with modern energy envelope, modular microgrid, and severe katabatic wind exposure.

### Core Objectives:
1. **Short-Term Power Demand Forecasting**: Predict station-level aggregate electrical and thermal power demand $P_{\text{demand}}(t + 1\,\text{h})$.
2. **Battery State-of-Charge (SoC) Forecasting**: Predict BESS charge/discharge dynamics to prevent deep-discharge degradation under sub-zero battery ambient conditions.
3. **Medium- & Long-Term Energy Demand**: Multi-horizon forecasting over 6-hour (generator staging) and 24-hour (day-ahead budget) horizons.
4. **Energy Deficit-Risk Prediction**: 1-hour ahead binary risk classification predicting whether battery SoC drops below 25% or demand exceeds 95% generator rated capacity.
5. **Generator Scheduling & Fuel Optimization**: Estimate optimal diesel generator loading points to minimize fuel burn rate while guaranteeing spinning reserves.
6. **Sensor ML Fusion**: Ingest upstream Sensor ML anomaly scores and health flags (`SPIKE`, `DRIFT`, `STUCK_VALUE`, `MISSING_DATA`) as contextual inputs.

---

## 2. Public Antarctic Data Investigation & Provenance

To ground our physics and environmental baselines in empirical Antarctic realities, we investigated available open-access scientific datasets:

### A. Australian Antarctic Division (AAD) / Australian Antarctic Data Centre (AADC)
- **Dataset Title:** *Monthly electricity usage at Casey, Davis, Mawson and Macquarie Island, January 1993 - February 2016*
- **Source Authority:** Australian Antarctic Data Centre (AADC), Department of Climate Change, Energy, the Environment and Water.
- **License:** Creative Commons Attribution 4.0 International ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
- **Temporal Coverage:** January 1993 – February 2016 (23 years of continuous station records).
- **Utility in Polarix:** Macroscopic empirical validation for Antarctic seasonal load curves.
- **Provenance Category:** `REAL_PUBLIC_ANTARCTIC_DATA` (Australian stations; **never** represented as Maitri or Bharati telemetry).

### B. National Centre for Polar and Ocean Research (NCPOR) / National Polar Data Centre (NPDC)
- **Dataset Title:** *Meteorological Observations from Indian Antarctic Stations (Maitri & Bharati)*
- **Source Authority:** NCPOR, Ministry of Earth Sciences, Government of India.
- **Utility in Polarix:** Establishes true environmental distribution bounds for temperature ($-50^\circ\text{C}$ to $+8^\circ\text{C}$), katabatic wind speeds, and seasonal polar daylight variations.
- **Provenance Category:** `REAL_PUBLIC_INDIAN_ANTARCTIC_WEATHER_DATA`.

---

## 3. Provenance Disclaimers & Synthetic Data Boundary

> [!IMPORTANT]
> **STRICT DATA PROVENANCE NOTICE:**
> 1. **No Public Operational Microgrid Energy Telemetry:** High-frequency sub-hourly microgrid telemetry for Maitri and Bharati is classified operational infrastructure data and **not publicly distributed**.
> 2. **Synthetic Operational Energy Telemetry:** To support high-resolution real-time forecasting and optimization, Polarix generates physically realistic, high-fidelity synthetic operational energy telemetry (`SYNTHETIC_POLARIX_OPERATIONAL_DATA`) conditioned on empirical Antarctic weather bounds, station thermal mass equations, and diurnal research activity cycles.
> 3. **Truth in Documentation:** We never label synthetic Maitri/Bharati power values as real historical telemetry.

---

## 4. Module Architecture

```text
ml/energy/
├── README.md                           # Architecture, Provenance & Subsystem Documentation
├── data/
│   ├── README.md                       # Canonical energy schema & feature dictionary
│   ├── energy_dataset_spec.json        # Schema & provenance contract
│   ├── ENERGY_DATASET_README.md        # Dataset generation equations & split boundaries
│   ├── generate_energy_dataset.py      # Deterministic physical dataset generator
│   ├── maitri_energy_telemetry.csv     # Maitri 1-year telemetry (8,760 rows)
│   ├── bharati_energy_telemetry.csv    # Bharati 1-year telemetry (8,760 rows)
│   ├── polarix_energy_telemetry.csv    # Combined multi-station telemetry (17,520 rows)
│   └── energy_dataset_manifest.json    # Machine-readable metadata & SHA-256 hashes
├── models/
│   ├── energy_lstm.py                  # PyTorch EnergyLSTM multi-task architecture & config
│   ├── energy_lstm_baseline.pt         # Saved neural baseline model weights
│   ├── energy_lstm_baseline_config.json# Model architecture configuration
│   ├── energy_lstm_baseline_scaler.json# Train-fit standard scaler parameters
│   ├── energy_deficit_risk_v1.joblib   # Saved Gradient Boosting deficit risk model bundle
│   └── energy_deficit_risk_v1_config.json # Deficit risk model metadata & frozen threshold
├── training/
│   ├── preprocessing.py                # Leakage-safe sequence builder & feature extraction
│   ├── baselines.py                    # Persistence, 24h Lag, & Moving Average baselines
│   └── train_baseline.py               # Deterministic training pipeline with early stopping
├── risk/
│   ├── __init__.py                     # Risk module export definitions
│   ├── features.py                     # Causal risk feature extraction & domain ratios
│   ├── models.py                       # Majority, Rule-Based, Logistic, and Gradient Boosting models
│   ├── train.py                        # Deficit risk training & threshold selection pipeline
│   ├── evaluate.py                     # Comprehensive test evaluation & cross-station transfer
│   └── inference.py                    # Canonical DeficitRiskForecaster inference engine
├── inference/
│   └── energy_forecaster.py            # Real-time multi-horizon forecaster engine
├── evaluation/
│   └── evaluate_baseline.py            # Multi-horizon forecast evaluation & benchmark reporting suite
├── results/
│   ├── baseline_metrics.json           # Disaggregated forecasting test metrics
│   ├── baseline_report.md              # Authoritative markdown forecasting report
│   ├── deficit_risk_metrics.json       # Disaggregated deficit risk classification metrics
│   └── deficit_risk_report.md          # Authoritative markdown deficit risk report
└── tests/
    ├── test_energy_dataset_spec.py     # Schema, provenance, and isolation tests
    ├── test_energy_dataset_generation.py# Physical constraints & dataset generation tests
    ├── test_energy_baseline.py         # 16-point unit, integration, and anti-leakage tests
    └── test_energy_deficit_risk.py     # 14-point risk classification & transfer tests
```

---

## 5. Forecasting Tasks & Baseline Performance

Evaluated on the held-out test partition (`2026-11-07T06:00:00Z` $\to$ `2026-12-31T23:00:00Z`):

| Forecasting Task | Target Variable | Horizon | Persistence MAE | Seasonal 24h Lag MAE | Neural LSTM MAE | Improvement vs Baseline | Neural $R^2$ |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **Task A** | `target_power_demand_1h_kw` | $t+1\,\text{h}$ | $5.17\,\text{kW}$ | $5.63\,\text{kW}$ | **$3.35\,\text{kW}$** | **$+35.1\%$** | **$0.631$** |
| **Task B** | `target_battery_soc_1h_percent` | $t+1\,\text{h}$ | $0.094\,\%$ | $0.137\,\%$ | **$0.067\,\%$** | **$+29.0\%$** | **$0.154$** |
| **Task C** | `target_energy_demand_6h_kwh` | $t+1..t+6\,\text{h}$ | $35.01\,\text{kWh}$ | $21.37\,\text{kWh}$ | **$13.46\,\text{kWh}$** | **$+37.0\%$** | **$0.862$** |
| **Task D** | `target_energy_demand_24h_kwh`| $t+1..t+24\,\text{h}$| $151.64\,\text{kWh}$ | $52.29\,\text{kWh}$ | **$41.92\,\text{kWh}$** | **$+18.9\%$** | **$0.862$** |

---

## 6. Energy Deficit-Risk Prediction Summary

- **Target:** `target_energy_deficit_risk` ($1$ if $\text{SoC}(t+1) < 25.0\%$ or $P_{\text{demand}}(t+1) > 0.95 \cdot P_{\text{rated}}$).
- **Horizon:** 1-Hour lookahead probability ($t \to t+1\,\text{h}$).
- **Feature Count:** 26 strictly causal physical, domain, temporal, and upstream sensor features.
- **Production Classifier:** `HistGradientBoostingClassifier` with balanced class weighting.
- **Operating Threshold:** $\tau = 0.3500$ (selected on validation partition to optimize F1 while enforcing $\ge 95\%$ recall).
- **Test Performance (Combined):**
  - **Accuracy:** $99.81\%$ ($N=2,626$ test observations)
  - **Precision:** $92.45\%$ ($49/53$)
  - **Recall:** $98.00\%$ ($49/50$ deficit events detected)
  - **F1 Score:** $0.9515$
  - **Specificity:** $99.84\%$ ($2,572/2,576$)
  - **ROC-AUC:** $0.9998$ | **PR-AUC:** $0.9921$
  - **Missed Deficit Rate:** $2.00\%$ ($1/50$)
- **Cross-Station Transfer Generalization:**
  - **MTR $\to$ BRT Test:** Recall $91.30\%$ ($21/23$), Precision $95.45\%$, ROC-AUC $0.9932$.
  - **BRT $\to$ MTR Test:** Recall $88.89\%$ ($24/27$), Precision $96.00\%$, ROC-AUC $0.9992$.

---

## 7. Leakage Prevention & Upstream Sensor ML Decoupling

1. **Chronological Splitting:** Strict 70% Train / 15% Val / 15% Test without temporal shuffling.
2. **Scaler Isolation:** Feature scalers are fit strictly on the train partition.
3. **Sequence & Rolling Window Independence:** Station features are generated within station boundaries; rolling means and slopes are strictly backward-looking.
4. **Sensor ML Decoupling:** Upstream Sensor ML anomaly features are ingested as input features; frozen Sensor ML models (`lstm-ae-v1.pt`, `lstm-ae-bharati-v1.pt`) remain completely untouched.

---

## 8. Unified Energy ML Inference Service & Backend Contract

To enable seamless, decoupled integration with Person A's backend services without modifying backend architecture prematurely, the Energy ML subsystem provides an orchestrator service:

- **Service Module:** `ml/energy/inference/energy_ml_service.py` (`EnergyMLService`)
- **Authoritative Contract:** `ml/energy/results/energy_ml_inference_contract.json`
- **Contract Version:** `energy-ml-contract-v1`
- **Unified Model Version:** `energy-ml-v1-candidate`
- **Model Status:** `CANDIDATE` (Validated strictly on synthetic Polarix operational microgrid telemetry; not on real classified station SCADA logs).

### Component Model Versioning & Horizons:
1. **Multi-Task EnergyLSTM Baseline (`lstm-energy-baseline-v1`):**
   - $P_{\text{demand}}(t+1\,\text{h})$ (1-Hour ahead load forecasting in kW)
   - $\text{SoC}(t+1\,\text{h})$ (1-Hour ahead battery state-of-charge in %)
   - $E_{\text{demand}}(t+1..t+6\,\text{h})$ (6-Hour cumulative energy budget in kWh)
   - $E_{\text{demand}}(t+1..t+24\,\text{h})$ (24-Hour cumulative day-ahead scheduling in kWh)
2. **Deficit-Risk Classifier (`energy-deficit-risk-v1`):**
   - 1-Hour ahead binary risk alarm probability ($t \to t+1\,\text{h}$)
   - Operating threshold: $\tau = 0.3500$ (dynamically loaded from artifact metadata)

### Temporal & Input Requirements:
- **Required Lookback:** Contiguous 24-hour causal telemetry window ($\ge 24$ hourly records).
- **Causal Guarantee:** Strictly contemporaneous and backward-looking ($t, t-1, \dots$). No future target columns are accepted or exposed during inference.

### Person A Backend Integration Boundary:
Person A backend services may consume the unified prediction contract (`UnifiedEnergyPrediction.to_dict()` or `energy_ml_service.predict(...)`) directly for REST/WebSocket dispatch once reviewed and integrated. ML internal weights, scalers, and feature engineering remain fully encapsulated.

---

## 9. Backend Integration Adapter (`EnergyMLBackendAdapter`)

To decouple backend streaming ingestion from batch neural sequence mechanics, Person C provides the `EnergyMLBackendAdapter` boundary adapter:

- **Adapter Module:** `ml/energy/inference/backend_adapter.py` (`EnergyMLBackendAdapter`)
- **Adapter Contract:** `ml/energy/results/energy_ml_backend_adapter_contract.json`
- **Compatibility Matrix:** `ml/energy/results/energy_ml_backend_compatibility_matrix.json`
- **Compatibility Report:** `ml/energy/results/energy_ml_backend_compatibility_report.md`

### Core Capabilities:
1. **Streaming Ingestion API:**
   - `adapter.ingest(telemetry: dict) -> AdapterResponse`
   - `adapter.predict(station_id: str) -> AdapterResponse`
   - `adapter.ingest_and_predict(telemetry: dict) -> AdapterResponse`
2. **Station Ring Buffers:** Maintains an isolated 24-hour sliding buffer per station (`MTR` and `BRT`). Histories are strictly segregated.
3. **Contiguous Hourly Continuity & Gap Detection:** Verifies consecutive hourly records ($\Delta t = 3600\,\text{s}$). Gaps or missing hours reset the contiguous lookback window.
4. **Insufficient History Status:** If $< 24$ contiguous hourly records exist, returns `status = "INSUFFICIENT_HISTORY"` with `available_history = N` without running neural inference on fabricated data.
5. **Prediction Available Status:** When 24 contiguous hourly records are buffered, returns `status = "PREDICTION_AVAILABLE"` with the full `UnifiedEnergyPrediction` payload (`energy-ml-contract-v1`).
6. **Station ID Validation & BHR Rejection:** Strictly accepts canonical station codes `MTR` and `BRT`. Rejects `BHR` with an explicit `ValueError` (no silent aliasing).
7. **Sensor ML Decoupling & Anomaly Ownership:** Ingests upstream `sensor_anomaly_score`, `sensor_anomaly_status`, and `data_quality` as contextual inputs with safe defaults (`1.0`, `"NORMAL"`, `"GOOD"`). Does not reclassify or alter Sensor ML anomaly outputs.
8. **Synthetic Telemetry Limitation:** Models are evaluated and calibrated against synthetic Polarix operational telemetry and public Antarctic meteorological envelopes; real classified station SCADA logs are not used.

---

## 10. Backend End-to-End Integration Harness

To validate the Energy ML subsystem against the canonical backend telemetry contract prior to Person A backend integration, Person C implemented an ML-side end-to-end simulation harness:

- **Integration Fixture:** `ml/energy/tests/fixtures/backend_telemetry_factory.py` (`BackendTelemetryFactory`)
- **End-to-End Test Suite:** `ml/energy/tests/test_energy_backend_e2e.py` (15 comprehensive integration tests)
- **Representative Contract Example:** `ml/energy/results/energy_ml_backend_e2e_example.json`

### Key Validated Properties:
1. **Canonical Telemetry Path:** Telemetry feeds purely canonical physical observations into `EnergyMLBackendAdapter.ingest()`. Target columns, ML features, and future values are strictly absent from incoming records.
2. **24-Hour History Buffering & Gap Recovery:** Verified that steps 1–23 return `INSUFFICIENT_HISTORY` (`prediction: null`), and step 24 returns `PREDICTION_AVAILABLE`. Timeline gaps $> 1\,\text{h}$ safely reset contiguous history without fabricating missing records.
3. **MTR / BRT Station Isolation:** Station streams interleaved in real time maintain completely separate buffers without cross-contamination.
4. **BHR Station ID Rejection:** Explicitly rejects legacy code `BHR` with a clear exception requiring backend normalization to `BRT` (zero silent aliasing).
5. **JSON Serialization & Zero Leakage:** Output payloads serialize strictly to standard JSON with zero NumPy scalar or PyTorch tensor leakage.
6. **Deterministic Inference:** Consecutive executions with identical telemetry produce bit-exact predictions across independent adapter instances.
7. **Failure Isolation:** Ingestion of malformed or invalid records is rejected cleanly without corrupting previously buffered valid history.
8. **Synthetic Data Limitation:** Provenance disclaimers strictly reflect that models are validated against synthetic Polarix operational microgrid telemetry and calibrated against public Antarctic meteorological envelopes, not classified real station SCADA records.

---

## 11. Energy ML Milestone Summary & Boundary Status

- **Milestone Manifest:** `ml/energy/results/energy_ml_milestone_manifest.json`
- **Implementation Status:** `VALIDATED_ML_MILESTONE`
- **Model Status:** `CANDIDATE`
- **Backend Integration Status:** `ML_SIDE_READY_BACKEND_PENDING`

### Implemented & Encapsulated:
- Synthetic Polarix microgrid operational telemetry generation (17,520 records; MTR & BRT).
- Multi-task EnergyLSTM neural network forecasting (1h load, 1h SoC, 6h energy, 24h energy).
- DeficitRiskForecaster Gradient Boosting classifier with tuned operational decision threshold ($\tau = 0.35$).
- Unified Energy ML service (`EnergyMLService`) generating unified output contract (`energy-ml-contract-v1`).
- Backend streaming adapter (`EnergyMLBackendAdapter`) with isolated 24-hour ring buffering per station.
- ML-side end-to-end integration harness and factory fixture (`BackendTelemetryFactory`).

### Validated:
- Causal, leakage-safe sequence preprocessing and strict temporal splitting.
- Deterministic, bit-exact inference across fresh adapter instances.
- 24-hour contiguous buffering, cold-start handling, and timeline gap recovery.
- Complete station buffer isolation between `MTR` and `BRT`.
- Strict rejection of legacy `BHR` with explicit normalization error.
- Corrupted/malformed input rejection without buffered history corruption.
- Pure JSON serialization safety with zero NumPy/PyTorch scalar leakage.
- Future mutation invariance (anti-leakage proof).

### Not Yet Implemented (Remaining Work / External Scope):
- Actual Person A backend operational integration into live FastAPI/Celery workers.
- Production Indian Antarctic station SCADA live feed integration.
- Model calibration against real classified station telemetry (subject to government operational data clearance).
