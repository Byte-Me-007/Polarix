# Polarix SIH 2026

## Person C — ML Specialist

### ML Scope
This module is dedicated to machine learning, telemetry anomaly detection, modeling, inference, and ML validation for the Polarix Antarctic Station Monitoring System (SIH26060).

> **Note on Telemetry:** Synthetic telemetry is used because real Maitri/Bharati historical sensor data is not assumed to be available.

---

### Station Development Rule
- **Maitri** is the first station target.
- **Bharati** will be implemented only after Maitri is completed and validated.

---

### Dataset Architecture & Generalization Fix (Step 5 Audit)
During the Step 5 audit of the model evaluation pipeline:
- **Root Cause Discovered**: The previous synthetic dataset generation mapped 1,000 timestamps across an incomplete fraction of a 24-hour diurnal cycle (period = 1,440 steps), meaning the 70% Train split covered only daytime peaks, while the 15% Test split covered nighttime troughs. Additionally, anomalies had been injected into Train and Val, leaving 0 anomalies in the Test partition.
- **Scientific Fix Applied**:
  1. Updated `ml/data/generate_maitri_dataset.py` with multi-cycle stationary diurnal periodicity (`day_period = 288`), ensuring normal means and standard deviations are statistically consistent across Train, Validation, and Test splits.
  2. Balanced anomaly injection: Training split (0-70%) is kept as 100% pure normal baseline data, while Validation (70-85%) and Test (85-100%) partitions receive balanced, independent distributions of all anomaly types (`SPIKE`, `DRIFT`, `DROPOUT`, `STUCK_VALUE`).
  3. Total dataset size: 10,000 rows (2,000 per sensor across 5 sensors).

---

### Implemented Baselines & Models

#### 1. Maitri Synthetic Telemetry Pipeline
- **Generator**: `ml/data/generate_maitri_dataset.py`
- **Output**: `ml/data/maitri_synthetic_telemetry.csv` (10,000 rows across 5 sensors)
- **Supported Anomaly Types**: `NORMAL`, `SPIKE`, `DRIFT`, `DROPOUT`, `STUCK_VALUE`
- **Sensors**: `TEMP_001` (°C), `PRESS_001` (hPa), `HUM_001` (%), `VIB_001` (mm/s), `POWER_001` (kW)

#### 2. Rolling Z-Score Anomaly Detector (`zscore-v1`)
- **Module**: `ml/training/zscore_detector.py`
- **Evaluation**: `ml/training/evaluate_zscore.py`
- **Methodology**:
  - Independent per-sensor trailing rolling mean and standard deviation.
  - **Leakage Prevention**: Only historical observations up to time $t$ are used; ground truth labels are strictly excluded during scoring.
  - **Dropout Handling**: Missing telemetry (`NaN`) is explicitly identified and classified as `MISSING_DATA`.
  - **Prediction Statuses**: `NORMAL`, `ANOMALY`, `MISSING_DATA`.
  - **Performance**:
    - Accuracy: 93.85%
    - Precision: 0.5816
    - Recall: 0.1285
    - F1-Score: 0.2105

#### 3. Maitri LSTM Autoencoder (`lstm-ae-v1`)
- **Model Definition**: `ml/training/lstm_autoencoder.py`
- **Sequence Preparation**: `ml/training/prepare_sequences.py`
- **Training Pipeline**: `ml/training/train_lstm_autoencoder.py`
- **Architecture**:
  - Sequence length: 30 time steps
  - Encoder LSTM: 32 hidden units, Latent Bottleneck: 16 units
  - Decoder LSTM: 32 hidden units, Linear Output projection
- **Training**:
  - Trained on 6,855 pure normal sequences.
  - Converged with final Training Loss = 0.014019, Best Validation Loss = 0.416389.

#### 4. Validation Threshold Selection & Test Evaluation (`lstm-ae-v1`)
- **Module**: `ml/training/select_lstm_threshold.py`
- **Threshold Selection**:
  - Optimized strictly on 1,181 Validation sequences to maximize F1-score.
  - **Selected Threshold**: `0.017674` (Validation F1 = 0.3972, Recall = 0.5925, Precision = 0.2988).
- **Frozen Test Evaluation (1,182 Test Sequences)**:
  - **Precision**: 0.2612
  - **Recall**: 0.5260
  - **F1-Score**: 0.3490
  - **Accuracy**: 52.03%
  - **Per-Anomaly-Type Breakdown**:
    - `SPIKE`: 19/19 detected (100.0% recall)
    - `DRIFT`: 127/150 detected (84.67% recall)
    - `STUCK_VALUE`: 6/120 detected (5.0% recall)
    - `NORMAL`: 463/893 correct (FPR = 48.15%)

#### 5. Real-Time Streaming ML Inference Layer (`LSTMAutoencoderInference`)
- **Module**: `ml/inference/lstm_inference.py`
- **Demo Script**: `ml/inference/run_maitri_inference_demo.py`
- **Purpose**: Exposes a clean, deterministic Python interface ready for Person A's backend telemetry stream integration.
- **Model & Artifacts Loaded**:
  - Model weights: `ml/models/lstm-ae-v1.pt`
  - Model configuration: `ml/models/lstm-ae-v1_config.json`
  - Persisted scalers: `ml/models/lstm-ae-v1_scaler.json`
  - Persisted threshold: `ml/results/lstm_threshold.json` (`threshold = 0.017674`)
- **Window Handling**:
  - Maintains isolated 30-step sliding history buffers per `(station_id, sensor_id)`.
  - First 29 observations return `"INSUFFICIENT_DATA"` with `anomaly_score = null`.
  - The 30th and subsequent observations compute the MSE reconstruction error and evaluate against the frozen validation threshold (`0.017674`).
- **Missing / Bad Quality Data Handling**:
  - Telemetry with `value = None`, `np.isnan(value)`, or `quality != "GOOD"` immediately returns `"MISSING_DATA"` with `anomaly_score = null` and resets the rolling window to prevent sequence corruption.
- **Result Contract**:
```json
{
  "station_id": "MTR",
  "sensor_id": "TEMP_001",
  "timestamp": "2026-03-01T00:29:00Z",
  "anomaly_score": 0.002824,
  "anomaly_status": "NORMAL",
  "model_version": "lstm-ae-v1"
}
```

---

### Maitri Model Comparison

A head-to-head comparison was conducted between the Rolling Z-Score baseline (`zscore-v1`) and the LSTM Autoencoder (`lstm-ae-v1`) on the corrected Maitri synthetic telemetry dataset.

> **Dataset Notice:** All metrics and evaluations reported below are derived from synthetic telemetry generated for Maitri station (`MTR`). No real Antarctic telemetry is claimed or used.

#### 1. Baseline & Model Rationale
- **Rolling Z-Score Baseline (`zscore-v1`)**: Simple, univariate statistical detector measuring standard score deviations relative to a 30-step trailing rolling window. Threshold is fixed at $3.0\sigma$.
- **LSTM Autoencoder (`lstm-ae-v1`)**: Deep sequence-to-sequence neural network learning compressed temporal representations (32 hidden units, 16 latent bottleneck units) across 30-step windows to detect multivariate temporal pattern deviations via reconstruction loss.

#### 2. Evaluation Methodology
- **Dataset Partitioning**: 10,000 synthetic records chronologically partitioned into Train (70%, 7,000 records, normal-only), Validation (15%, 1,500 records), and Test (15%, 1,500 records) across 5 sensors.
- **Leakage Prevention**: The LSTM decision threshold (`0.017674`) was tuned exclusively on Validation data to maximize F1-score and frozen. Test split remained untouched during selection.
- **Missing Data Handling**: Dropout telemetry (`NaN`) is categorized as `MISSING_DATA` at ingestion/inference; in LSTM sequence processing, sequences with missing steps are handled explicitly.

#### 3. Measured Results Summary

| Metric | Rolling Z-Score (`zscore-v1`) | LSTM Autoencoder (`lstm-ae-v1`) |
| :--- | :--- | :--- |
| **Threshold Strategy** | Heuristic ($3.0\sigma$) | Validation F1-Tuned ($0.017674$) |
| **Validation Precision / Recall / F1** | 0.6780 / 0.1246 / 0.2105 | 0.2988 / 0.5925 / 0.3972 |
| **Validation Accuracy** | 80.00% | 55.55% |
| **Test Precision / Recall / F1** | **0.7119 / 0.1325 / 0.2234** | **0.2612 / 0.5260 / 0.3490** |
| **Test Accuracy** | 80.53% | 52.03% |
| **Test TP / TN / FP / FN** | 42 / 1166 / 17 / 275 | 152 / 463 / 430 / 137 |

#### 4. Anomaly-Type & False-Alarm Behavior (Test Set)

| Anomaly Type / Class | Total Instances | Z-Score Detected (Recall) | LSTM-AE Detected (Recall) |
| :--- | :--- | :--- | :--- |
| **`SPIKE`** | 19 | 10 (52.63%) | 19 (100.0%) |
| **`DRIFT`** | 150 | 4 (2.67%) | 127 (84.67%) |
| **`STUCK_VALUE`** | 120 | 0 (0.00%) | 6 (5.00%) |
| **`DROPOUT`** | 28 | 28 (100.0% via `MISSING_DATA`) | Handled via missing quality rule |
| **`NORMAL` (False Alarms)** | 1183 (Z) / 893 (LSTM) | 17 (FPR = 1.44%) | 430 (FPR = 48.15%) |

#### 5. Behavioral Analysis & Model Limitations
- **Spike Detection**: LSTM Autoencoder captured 100% of sudden spike anomalies; Z-score detected 52.63% (missing lower-magnitude sudden shocks within $\pm 3\sigma$).
- **Drift Detection**: LSTM Autoencoder detected 84.67% of gradual drift anomalies due to sequence-level pattern sensitivity; Z-score detected 2.67% because the trailing rolling mean dynamically adjusted to gradual shifts.
- **Stuck Flatlines**: Both architectures exhibited low sensitivity on mid-range stuck values (Z-score: 0.0%, LSTM-AE: 5.0%), as flatline values remained within normal sensor operating ranges without explicit rolling variance features.
- **False Alarm Trade-off**: Z-score achieved low false alarm rate (1.44% FPR, Precision = 0.7119) with low recall (13.25%). The LSTM Autoencoder achieved higher recall (52.60%, F1 = 0.3490) while incurring a higher false positive rate (48.15% FPR, Precision = 0.2612) on normal diurnal fluctuations.

---

### ML Integration Contract

A stable, typed interface is defined in `ml/inference/inference_contract.py` for Person A (Backend) to stream telemetry into the ML inference engine without coupling to internal PyTorch mechanics.

> **Backend Independence**: The ML inference contract relies strictly on standard library dataclasses and JSON structures. It does not depend on FastAPI, MQTT, or backend databases and is fully prepared for backend integration.

#### 1. Input Contract Schema (`TelemetryInput`)
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

#### 2. Output Contract Schema (`TelemetryInferenceOutput`)
```json
{
  "station_id": "MTR",
  "sensor_id": "TEMP_001",
  "timestamp": "2026-09-17T10:30:00Z",
  "value": -34.5,
  "unit": "C",
  "quality": "GOOD",
  "source": "SIMULATOR",
  "anomaly_score": 0.0215,
  "anomaly_status": "ANOMALY",
  "anomaly_type": "SPIKE",
  "model_version": "lstm-ae-v1"
}
```

#### 3. Supported Scope & Validation
- **Supported Station**: `MTR` (Maitri only). Non-Maitri stations raise `UnsupportedStationError`.
- **Supported Sensors**: `TEMP_001`, `PRESS_001`, `HUM_001`, `VIB_001`, `POWER_001`. Unsupported sensors raise `UnsupportedSensorError`.

#### 4. Operational Inference Statuses & Anomaly Types
- **`INSUFFICIENT_DATA`**: The sliding history window has fewer than 30 consecutive observations (`anomaly_score = null`, `anomaly_type = null`).
- **`NORMAL`**: 30-step window reconstruction error $\le 0.017674$ (`anomaly_score` MSE, `anomaly_type = "NORMAL"`).
- **`ANOMALY`**: 30-step window reconstruction error $> 0.017674$ (`anomaly_score` MSE, `anomaly_type` evaluated via `AnomalyTypeClassifier`).
- **`MISSING_DATA`**: Incoming telemetry has `value = null`, `NaN`, or `quality != "GOOD"` (`anomaly_score = null`, `anomaly_type = null`).

#### 5. Reconstruction Error Scoring
- `anomaly_score` represents the exact Mean Squared Error (MSE) between the normalized input sequence and the autoencoder reconstruction.
- Scores are raw reconstruction errors, NOT probabilities or percentages, preserving physical interpretability against the validated threshold (`0.017674`).

---

### Anomaly Type Classification Layer

While the LSTM Autoencoder reliably detects that a temporal window is anomalous via reconstruction loss, reconstruction error alone does not differentiate between distinct physical failure modes. The `AnomalyTypeClassifier` (`ml/inference/anomaly_type_classifier.py`) provides an interpretable, deterministic rule layer operating directly on the 30-step telemetry window.

> **Telemetry Notice:** Evaluated purely on synthetic Maitri telemetry (`MTR`). Does not claim real Antarctic operational validation or clinical perfection.

#### 1. Supported Anomaly Class Definitions
- **`SPIKE`**: Short-lived, high-magnitude jump or abrupt step change ($\ge 3.5\times$ jump ratio / isolated pulse relative to noise baseline).
- **`DRIFT`**: Gradual, sustained directional shift across the 30-step window (linear trend $|r| \ge 0.70$, directional consistency ratio $\ge 0.45$, without dominating single-step spikes).
- **`STUCK_VALUE`**: Frozen/constant telemetry with near-zero local standard deviation ($\le 10^{-4}$) or $\ge 8$ consecutive identical/near-identical observations.
- **`NORMAL`**: Stationary baseline telemetry within standard noise envelopes.
- **`UNKNOWN`**: Explicit category assigned when an anomalous window does not match singular archetype criteria with high confidence.
- **`DROPOUT`**: Telemetry missingness (`null`, `NaN`, non-GOOD quality) is preserved as `MISSING_DATA` and excluded from numeric anomaly type classification.

#### 2. Calibration & Validation Methodology
- **Leakage Prevention**: Classification rules rely solely on mathematical signal properties and training-normal noise distributions. No ground truth labels or test partition data are used to tune classifier thresholds.
- **Validation Evaluation**: Evaluated across 1,327 test windows in `ml/results/maitri_anomaly_type_validation.json`:
  - `SPIKE`: 19/19 detected (100% recall)
  - `DRIFT`: 27 true positives, with subtle/early ramps falling into UNKNOWN or SPIKE
  - `STUCK_VALUE`: Evaluated against primary detector output
  - `UNKNOWN`: 15.6% assignment rate on ambiguous multi-pattern fluctuations

#### 3. Limitations
- Single-point spikes embedded within drifting series can be classified as SPIKE due to high first-difference dominance.
- Mid-range stuck values that do not trigger the primary LSTM reconstruction threshold remain classified as NORMAL unless paired with explicit variance features.

---

### Model Registry & Integrity Management

A cryptographic model registry layer (`ml/models/model_registry.py`) and manifest schema (`ml/models/lstm-ae-v1_manifest.json`) are established to enforce reproducible artifact tracking and integrity verification.

> **Telemetry & Operational Scope Notice:** Model versioning provides deterministic artifact traceability on synthetic telemetry. It does not imply operational certification or real-world Antarctic telemetry validation.

#### 1. Registered Model Version: `lstm-ae-v1`
- **Station ID**: `MTR` (Maitri)
- **Supported Sensors**: `TEMP_001`, `PRESS_001`, `HUM_001`, `VIB_001`, `POWER_001`
- **Architecture**: Sequence-to-sequence LSTM Autoencoder (window = 30, hidden = 32, latent = 16)
- **Loss Function**: MSELoss
- **Training Dataset**: `ml/data/maitri_synthetic_telemetry.csv` (`10k_stationary_diurnal_v1`, seed = 42, 70% pure normal baseline)

#### 2. Registered Artifact Manifest & Checksums
| Artifact Role | Relative Path | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **Model Weights** | `ml/models/lstm-ae-v1.pt` | 50,613 | `7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262` |
| **Hyperparameters** | `ml/models/lstm-ae-v1_config.json` | 187 | `71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b` |
| **Sensor Scalers** | `ml/models/lstm-ae-v1_scaler.json` | 657 | `2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224` |
| **Validation Threshold** | `ml/results/lstm_threshold.json` | 493 | `80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1` |

#### 3. Integrity Verification Workflow
- **Pre-Execution Validation**: `LSTMAutoencoderInference` performs strict cryptographic SHA-256 and byte-size verification against `lstm-ae-v1_manifest.json` before instantiating PyTorch tensors or loading scalers.
- **Tampering & Corruption Protection**: If any artifact file is modified, corrupted, or missing, `validate_model_artifacts()` immediately aborts with `ModelIntegrityError`, preventing silent drift or corrupted inference execution.
- **Standalone Validation**:
  ```python
  from ml.models.model_registry import validate_model_artifacts
  report = validate_model_artifacts("lstm-ae-v1", raise_on_error=True)
  ```

---

---

### End-to-End Maitri ML Validation

The complete end-to-end ML inference pipeline is validated via `ml/inference/validate_maitri_pipeline.py` and tested under `ml/tests/test_maitri_end_to_end_pipeline.py`.

> **Dataset & Scope Notice:** All validation is performed strictly on synthetic telemetry generated for Maitri station (`MTR`). No real Antarctic deployment, historical Maitri data, production readiness, perfect anomaly detection, or guaranteed operational reliability is claimed.

#### 1. End-to-End Pipeline Flow
```text
TelemetryInput
  → Contract validation (Schema, station, sensor)
  → Model integrity validation (SHA-256 Checksums)
  → Rolling window buffer (30-step minimum per sensor)
  → LSTM reconstruction error (MSE vs threshold 0.017674)
  → Anomaly status (NORMAL / ANOMALY / INSUFFICIENT_DATA / MISSING_DATA)
  → Anomaly type classification (SPIKE / DRIFT / STUCK_VALUE / NORMAL / UNKNOWN)
  → TelemetryInferenceOutput (Typed contract)
  → JSON Serializable Result
```

#### 2. Key Pipeline Architectural Guarantees
- **30-Observation Minimum Window**: Observations 1 to 29 yield `INSUFFICIENT_DATA` (`anomaly_score = null`, `anomaly_type = null`). Scored inference begins strictly upon reaching 30 valid observations.
- **Per-Sensor History Isolation**: Each sensor (`TEMP_001`, `PRESS_001`, `HUM_001`, `VIB_001`, `POWER_001`) maintains an isolated sliding deque buffer. Interleaving observations across multiple sensors never causes cross-sensor buffer contamination.
- **Missing Data Handling**: Telemetry with `value = None`, `NaN`, or non-GOOD quality (`BAD`, `MISSING`, `UNCERTAIN`) immediately produces `MISSING_DATA` (`anomaly_score = null`, `anomaly_type = null`) and clears the rolling window to prevent sequence contamination.
- **Model Version Propagation**: The model version string (`lstm-ae-v1`) is deterministically propagated through all output contracts.
- **Model Integrity Enforcement**: Cryptographic SHA-256 checksums and file sizes for all registered model artifacts (`lstm-ae-v1.pt`, `lstm-ae-v1_config.json`, `lstm-ae-v1_scaler.json`, `lstm_threshold.json`) are verified prior to inference execution.
- **Pipeline Correctness vs. Model Accuracy**: Pipeline validation tests assert structural correctness, contract integrity, isolation, state handling, and JSON serialization independently of model false positive variations on synthetic signals.

#### 3. Validation Summary (`ml/results/maitri_end_to_end_validation.json`)
- **Overall Status**: `PASS`
- **Total Telemetry Records Processed**: 1,093
- **Sensors Tested**: `TEMP_001`, `PRESS_001`, `HUM_001`, `VIB_001`, `POWER_001`
- **Scenarios Evaluated**:
  1. `NORMAL`: Initial 29 steps return `INSUFFICIENT_DATA`; valid steps output `NORMAL` status with `anomaly_type = "NORMAL"`.
  2. `SPIKE`: Abrupt pulses trigger `ANOMALY` with `anomaly_type = "SPIKE"` or `"UNKNOWN"`.
  3. `DRIFT`: Sustained monotonic ramps trigger `ANOMALY` with `anomaly_type = "DRIFT"` or `"UNKNOWN"`.
  4. `STUCK_VALUE`: Flatline values trigger `ANOMALY` with `anomaly_type = "STUCK_VALUE"` or `"UNKNOWN"`.
  5. `DROPOUT_MISSING_DATA`: Null values and bad quality tags return `MISSING_DATA` and reset rolling buffers.
  6. `INSUFFICIENT_DATA`: Sequences $<30$ steps return `INSUFFICIENT_DATA`.
  7. `MULTI_SENSOR_ISOLATION`: Interleaved multi-sensor observations maintain independent histories without cross-talk.
  8. `MODEL_INTEGRITY`: Artifact checksums and byte sizes match manifest specifications.
  9. `JSON_SERIALIZATION`: Complete round-trip serialization between typed contracts and JSON.

---

---

### Maitri ML Service Boundary

The `MaitriMLService` (`ml/inference/maitri_ml_service.py`) provides a clean, framework-independent service adapter for downstream consumption by Person A's backend or other orchestrators.

> **Service Boundary Scope Notice:** This is an **ML-side service boundary**, NOT the FastAPI backend. It contains zero web/API framework dependencies and operates purely on typed standard-library contracts.

#### 1. Why the Adapter Exists
- **Decoupling**: Enables the backend to stream telemetry and receive anomaly detection outputs without coupling to internal PyTorch mechanics, sequence reshaping, scaler transforms, or classifier rule details.
- **Single Point of Orchestration**: Provides a unified, minimal entrypoint (`process_telemetry`) that encapsulates contract validation, artifact verification, sliding buffer management, LSTM inference, and anomaly type categorization.

#### 2. Downstream Consumption Pattern
```python
from ml.inference.inference_contract import TelemetryInput
from ml.inference.maitri_ml_service import MaitriMLService

# 1. Initialize service once on backend startup
ml_service = MaitriMLService()

# 2. Process incoming telemetry in ingestion worker / MQTT handler
input_data = TelemetryInput(
    station_id="MTR",
    sensor_id="TEMP_001",
    timestamp="2026-09-18T10:00:00Z",
    value=-15.2,
    unit="°C",
    quality="GOOD",
)
output = ml_service.process_telemetry(input_data)

# 3. Consume typed output contract
print(output.anomaly_status)  # "NORMAL", "ANOMALY", "INSUFFICIENT_DATA", "MISSING_DATA"
print(output.anomaly_score)   # MSE reconstruction error (float or None)
print(output.anomaly_type)    # "SPIKE", "DRIFT", "STUCK_VALUE", "NORMAL", "UNKNOWN" (or None)
```

#### 3. Core Architectural Properties
- **Framework-Independent**: Pure Python implementation with zero dependency on FastAPI, MQTT, SQLite, WebSockets, or UI frameworks.
- **Component Reuse**: Reuses the validated `LSTMAutoencoderInference`, `AnomalyTypeClassifier`, and `model_registry` directly without duplicating inference or classification logic.
- **Pre-Execution Integrity Enforcement**: Automatically verifies cryptographic SHA-256 checksums and file sizes against `lstm-ae-v1_manifest.json` upon initialization.
- **Zero Online Retraining**: Model weights (`lstm-ae-v1.pt`), scalers (`lstm-ae-v1_scaler.json`), and decision threshold (`0.017674`) remain strictly frozen during inference execution.
- **Per-Sensor Isolation & State Management**: Maintains isolated 30-step sliding history deques for each supported sensor (`TEMP_001`, `PRESS_001`, `HUM_001`, `VIB_001`, `POWER_001`). Exposes `reset_sensor(sensor_id)` and `reset_all()` APIs for explicit state control.

---

---

### Maitri LSTM Calibration Analysis

A comprehensive threshold calibration analysis was conducted in `ml/training/analyze_lstm_calibration.py` to evaluate the operating characteristics and trade-offs of the frozen reconstruction threshold (`0.017674`) across multiple candidate operating points.

> **Dataset Notice & Calibration Disclaimer:** All calibration analyses are performed on synthetic Maitri telemetry (`MTR`). Calibration on synthetic signals demonstrates mathematical operating trade-offs and does NOT constitute real Antarctic validation, operational certification, or high-reliability guarantees.

#### 1. Methodological Principles
- **Validation-Only Selection**: Candidate operating points are tuned/selected strictly on the Validation split (1,181 sequences).
- **Frozen Test Evaluation**: Operating points are evaluated on the untouched Test split (1,182 sequences) without feedback or threshold adjustment.
- **Label Leakage Prevention**: Ground-truth anomaly labels are strictly excluded during production scoring and used only for offline evaluation.
- **Dropout Exclusion**: `DROPOUT` instances are handled via the missing-data contract ingestion rule (`quality != 'GOOD'`) and excluded from numeric LSTM reconstruction-error calculations.

#### 2. Evaluated Operating Points

| Operating Point | Threshold (MSE) | Selection Criterion | Test Precision | Test Recall | Test F1 | Test FPR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`CURRENT_FROZEN`** | **0.017674** | Validation F1-optimal (Step 4 frozen baseline) | **0.2612** | **0.5260** | **0.3490** | **0.4815** |
| **`VAL_MAX_F1`** | 0.017240 | Validation grid search maximizing F1 | 0.2602 | 0.5294 | 0.3489 | 0.4871 |
| **`HIGH_RECALL_85`** | 0.000690 | Target Validation Recall $\ge 85\%$ | 0.2445 | 1.0000 | 0.3929 | 1.0000 |
| **`LOWER_FPR_20`** | 0.687772 | Constrain Validation FPR $\le 20\%$ | 0.0955 | 0.0519 | 0.0673 | 0.1590 |
| **`PERCENTILE_90_NORMAL`** | 1.972147 | 90th percentile of normal validation errors | 0.0132 | 0.0035 | 0.0055 | 0.0840 |
| **`PERCENTILE_95_NORMAL`** | 2.963099 | 95th percentile of normal validation errors | 0.0000 | 0.0000 | 0.0000 | 0.0090 |
| **`PERCENTILE_99_NORMAL`** | 3.622379 | 99th percentile of normal validation errors | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

#### 3. Core Trade-off Findings & Limitations
- **Precision / Recall Trade-off**: The current production threshold (`0.017674`) represents the best balance for detecting subtle temporal anomalies (`SPIKE`: 100% recall, `DRIFT`: 84.67% recall) with moderate F1 ($0.3490$), but incurs a $48.15\%$ false positive rate on normal diurnal cycles.
- **Extreme False-Positive Suppression Risks**: Raising the threshold to percentile-based levels (e.g. 95th percentile $= 2.963$) successfully reduces false positive rate to $0.90\%$, but causes anomaly recall to collapse to $0.00\%$ because reconstruction errors for subtle drifts ($0.02 - 0.20$) lie below normal signal peak variations.
- **Anomaly-Specific Sensitivity**: Single-threshold reconstruction loss cannot reliably isolate mid-range flatlines (`STUCK_VALUE`) without complementary statistical features (e.g., local variance).

---

### Maitri ML Inference Reliability

A comprehensive reliability audit and hardening layer is implemented across `ml/inference/inference_contract.py`, `ml/inference/lstm_inference.py`, and `ml/inference/maitri_ml_service.py` to ensure that malformed, delayed, duplicate, non-finite, or corrupted telemetry records never silently produce misleading ML anomaly scores.

> **Validation & Telemetry Disclaimer:** Evaluated purely via deterministic offline validation and synthetic Maitri telemetry (`MTR`). No claims of real Antarctic operational validation, field readiness, or clinical perfection are made.

#### 1. Why Streaming Telemetry Validation Matters
In operational streaming architectures, sensors and network transmitters frequently encounter transient dropped packets, micro-reboots, clock jitter, duplicate message deliveries, and hardware ADC saturation. Without strict inference-layer validation, non-finite numbers (`NaN`, `+inf`, `-inf`) can silently propagate through neural networks, yielding invalid NaN loss tensors or unhandled floating-point exceptions. Similarly, out-of-order or duplicate records can distort sliding sequence temporal order, leading to spurious false alarms or undetected anomalies.

#### 2. Non-Finite Value Handling
- Any telemetry record carrying a non-finite numerical value (`NaN`, `+inf`, `-inf`, or non-numeric object) is strictly intercepted before reaching the scaler or PyTorch neural network.
- The pipeline immediately routes the record to `MISSING_DATA` status with `anomaly_score = null` and `anomaly_type = null`.
- The sensor's rolling history window is cleared to prevent mathematical sequence corruption.

#### 3. Missing-Data Handling
- Telemetry with `value = None` or invalid/non-GOOD telemetry quality (`BAD`, `MISSING`, `UNCERTAIN`) cleanly returns `MISSING_DATA` (`anomaly_score = null`, `anomaly_type = null`).
- The sensor's rolling buffer is immediately reset so that gaps in continuous telemetry do not result in synthetic step-jumps or distorted reconstruction errors.

#### 4. Duplicate and Out-of-Order Telemetry Policy
- **Chronological Tracking**: The inference engine tracks the latest ingested timestamp per `(station_id, sensor_id)` pair.
- **Duplicate Timestamps**: If an exact duplicate timestamp arrives for an active sensor, the service raises `DuplicateTelemetryError`. The observation is not appended twice and the rolling buffer is not artificially advanced.
- **Out-of-Order Telemetry**: If a stale observation arrives with a timestamp older than the most recently processed timestamp, the service raises `StaleTelemetryError`. The chronological sequence in the buffer is preserved without corruption.

#### 5. Sensor & Station Isolation
- Each supported Maitri sensor (`TEMP_001`, `PRESS_001`, `HUM_001`, `VIB_001`, `POWER_001`) maintains an entirely isolated sliding deque buffer.
- Interleaved multi-sensor telemetry streams (e.g. `TEMP_001` followed by `PRESS_001`) process independently without cross-talk or shared state contamination.
- Maitri (`MTR`) remains the sole supported station; requests specifying unsupported stations (e.g. `BHARATI` or `BHT`) are rejected with `UnsupportedStationError`.

#### 6. Bounded Rolling Window & Reset Behavior
- Rolling buffers are backed by `collections.deque(maxlen=30)`, ensuring strict $O(1)$ constant memory overhead with zero unbounded memory growth regardless of stream duration.
- `reset_sensor(sensor_id)` flushes history for only the specified sensor without impacting other sensors.
- `reset_all()` provides a full station-level state reset.

#### 7. Model Integrity & Deterministic Inference
- Pre-execution SHA-256 and byte-size verification against `lstm-ae-v1_manifest.json` ensures inference cannot proceed if model weights, configurations, scalers, or thresholds are tampered with or missing.
- Identical telemetry sequences fed into separate service instances produce bit-for-bit identical outputs without non-deterministic side effects or unhandled serialization types.

#### 8. Synthetic Data Limitation
- All reliability guarantees are validated on deterministic synthetic datasets. Real-world physical anomalies, radio noise, and hardware degradation modes may present behaviors not fully captured in synthetic sequences.

---

### Directory Layout
- `ml/data/`: Data storage and synthetic generation scripts (`maitri_synthetic_telemetry.csv`).
- `ml/models/`: Serialized model weights (`lstm-ae-v1.pt`), scalers, configs, model registry (`model_registry.py`), and version manifests (`lstm-ae-v1_manifest.json`).
- `ml/training/`: Training scripts, baseline detectors (`zscore_detector.py`), autoencoder (`lstm_autoencoder.py`, `train_lstm_autoencoder.py`), threshold selection (`select_lstm_threshold.py`), model comparison (`compare_models.py`), calibration analysis (`analyze_lstm_calibration.py`), and anomaly classifier evaluation (`evaluate_anomaly_classifier.py`).
- `ml/inference/`: Production ML service adapter (`maitri_ml_service.py`), inference service (`lstm_inference.py`), anomaly type classifier (`anomaly_type_classifier.py`), typed integration contracts (`inference_contract.py`), reliability validation script (`validate_maitri_inference_reliability.py`), pipeline validation harness (`validate_maitri_pipeline.py`), service demo (`run_maitri_service_demo.py`), and streaming demos.
- `ml/forecasting/`: Predictive telemetry forecasting modules.
- `ml/tests/`: Pytest test suite (`test_maitri_inference_reliability.py`, `test_lstm_calibration_analysis.py`, `test_maitri_ml_service.py`, `test_maitri_end_to_end_pipeline.py`, `test_model_registry.py`, `test_anomaly_type_classifier.py`, `test_inference_contract.py`, `test_lstm_inference.py`, etc.).
- `ml/results/`: Evaluation predictions, metrics JSON, comparison reports (`maitri_model_comparison.json`), calibration reports (`maitri_lstm_calibration_analysis.json`, `maitri_lstm_operating_points.csv`), reliability report (`maitri_inference_reliability.json`), calibration plots, end-to-end validation report (`maitri_end_to_end_validation.json`), anomaly type validation artifacts, registry validation reports, and contract examples.



