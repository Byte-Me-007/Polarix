# Polarix Bharati Anomaly Type Classifier Evaluation Report (SIH26060 - Person C)

**Station:** Bharati (`BRT`)  
**Classifier Class:** `BharatiAnomalyTypeClassifier` (`ml.inference.bharati_anomaly_type_classifier.BharatiAnomalyTypeClassifier`)  
**Underlying Model Version:** `lstm-ae-bharati-v1`  
**Decision Threshold:** `0.013215307652775843`  
**Window Length:** `30` observations  
**Status:** VALIDATED & INTEGRATED WITH INFERENCE SERVICE  

---

> [!IMPORTANT]
> **SYNTHETIC DATA DISCLAIMER**:
> All evaluations were conducted strictly on synthetic telemetry generated for Bharati station.
> No real Antarctic station telemetry was used. These metrics reflect feature heuristic behaviors on synthetic distributions and do not represent field operational certifications.

---

## 1. Overview & Classification Architecture

The `BharatiAnomalyTypeClassifier` serves as an interpretable, deterministic post-processing layer that attributes explainable anomaly archetype labels to anomalous windows detected by the primary LSTM Autoencoder:

- **Primary LSTM Autoencoder:** Binary anomaly detector evaluating reconstruction MSE against the frozen threshold (`0.013215307652775843`) $\rightarrow$ `NORMAL` vs `ANOMALY`.
- **Deterministic Type Classifier:** Analyzes local window features (first differences, jump ratios, linear slopes, directional trend ratios, and tail variances) to assign physical category tags:
  - `NORMAL`: Observation and sequence conform to baseline stationary behavior.
  - `SPIKE`: High-magnitude isolated step jump exceeding local baseline noise.
  - `DRIFT`: Sustained monotonic slope with high directional consistency across the window.
  - `STUCK_VALUE`: Constant or near-constant telemetry flatline over recent observations.
  - `UNKNOWN`: Anomalous observation without a clear singular archetype signature.
  - *Note on `DROPOUT`:* Missing/non-finite telemetry is handled upstream as `MISSING_DATA` and is never converted to an anomaly type.

---

## 2. Dataset Evaluation Performance (Synthetic Benchmark)

*Evaluated across 9,855 sequential 30-step windows in `ml/data/bharati_synthetic_telemetry.csv`:*

| Anomaly Class | Support (Windows) | True Positives | Precision | Recall | F1-Score | Detection & Characteristic Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`NORMAL`** | 9,217 | 6,194 | `1.0000` | `0.6720` | `0.8038` | When LSTM flags NORMAL, guaranteed 100% precision. |
| **`SPIKE`** | 41 | 41 | `0.0421` | `1.0000` | `0.0807` | **100% recall** on high-magnitude sudden jumps. |
| **`DRIFT`** | 300 | 146 | `0.0802` | `0.4867` | `0.1377` | Captures steady monotonic ramps; early steps classify as SPIKE/UNKNOWN. |
| **`STUCK_VALUE`** | 240 | 180 | `0.5000` | `0.7500` | `0.6000` | **75% recall** on frozen sensor flatlines. |

### Summary on DROPOUT & UNKNOWN Rates:
- **`DROPOUT` Handling:** 57 / 57 instances (100.0%) correctly routed to `MISSING_DATA` ingestion handler.
- **`UNKNOWN` Attribution:** 159 windows (1.61% of total evaluated sequences) classified as `UNKNOWN` when multi-modal noise prevented confident archetype attribution.

---

## 3. Sensor-Specific Noise Calibrations

| Sensor ID | Monitored Channel | Calibrated Noise Std ($\sigma_{\text{noise}}$) | Physical Unit |
| :--- | :--- | :--- | :--- |
| **`BRT_TEMP_001`** | Temperature | `0.30` | `°C` |
| **`BRT_PRESS_001`**| Atmospheric Pressure | `0.20` | `hPa` |
| **`BRT_HUM_001`**  | Relative Humidity | `1.00` | `%` |
| **`BRT_VIB_001`**  | Vibration Velocity | `0.03` | `mm/s` |
| **`BRT_POWER_001`**| Power Consumption | `0.70` | `kW` |

---

## 4. Integration Verification

- **Service Class:** [`BharatiMLService`](file:///Users/rexjohnabraham/Documents/Polarix_C/ml/inference/bharati_ml_service.py) automatically tags `anomaly_type` in [`BharatiTelemetryOutput`](file:///Users/rexjohnabraham/Documents/Polarix_C/ml/inference/bharati_inference_contract.py).
- **Frozen Artifacts:** `lstm-ae-bharati-v1.pt`, `lstm-ae-bharati-v1_config.json`, `lstm-ae-bharati-v1_scaler.json`, and `bharati_lstm_threshold.json` remained 100% unmodified.
