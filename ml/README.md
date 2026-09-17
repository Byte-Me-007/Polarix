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
  "model_version": "lstm-ae-v1"
}
```

#### 3. Supported Scope & Validation
- **Supported Station**: `MTR` (Maitri only). Non-Maitri stations raise `UnsupportedStationError`.
- **Supported Sensors**: `TEMP_001`, `PRESS_001`, `HUM_001`, `VIB_001`, `POWER_001`. Unsupported sensors raise `UnsupportedSensorError`.

#### 4. Operational Inference Statuses
- **`INSUFFICIENT_DATA`**: The sliding history window has fewer than 30 consecutive observations. `anomaly_score` is `null`.
- **`NORMAL`**: 30-step window reconstruction error $\le 0.017674$. `anomaly_score` contains the raw MSE reconstruction error.
- **`ANOMALY`**: 30-step window reconstruction error $> 0.017674$. `anomaly_score` contains the raw MSE reconstruction error.
- **`MISSING_DATA`**: Incoming telemetry has `value = null`, `NaN`, or `quality != "GOOD"`. `anomaly_score` is `null`, and the sensor's rolling buffer is reset to avoid contaminated windows.

#### 5. Reconstruction Error Scoring
- `anomaly_score` represents the exact Mean Squared Error (MSE) between the normalized input sequence and the autoencoder reconstruction.
- Scores are raw reconstruction errors, NOT probabilities or percentages, preserving physical interpretability against the validated threshold (`0.017674`).

---

### Directory Layout
- `ml/data/`: Data storage and synthetic generation scripts (`maitri_synthetic_telemetry.csv`).
- `ml/models/`: Serialized model weights (`lstm-ae-v1.pt`), scalers, and configs.
- `ml/training/`: Training scripts, baseline detectors (`zscore_detector.py`), autoencoder (`lstm_autoencoder.py`, `train_lstm_autoencoder.py`), threshold selection (`select_lstm_threshold.py`), and model comparison (`compare_models.py`).
- `ml/inference/`: Production inference service (`lstm_inference.py`), typed integration contracts (`inference_contract.py`), contract demo (`run_maitri_contract_demo.py`), and streaming demo (`run_maitri_inference_demo.py`).
- `ml/forecasting/`: Predictive telemetry forecasting modules.
- `ml/tests/`: Pytest test suite (`test_inference_contract.py`, `test_lstm_inference.py`, etc.).
- `ml/results/`: Evaluation predictions, metrics JSON, comparison reports (`maitri_model_comparison.json`, `maitri_model_comparison.csv`), visualization figures, and contract examples (`maitri_inference_contract_example.json`).
