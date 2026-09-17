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

### Directory Layout
- `ml/data/`: Data storage and synthetic generation scripts (`maitri_synthetic_telemetry.csv`).
- `ml/models/`: Serialized model weights (`lstm-ae-v1.pt`), scalers, and configs.
- `ml/training/`: Training scripts, baseline detectors (`zscore_detector.py`), autoencoder (`lstm_autoencoder.py`, `train_lstm_autoencoder.py`), threshold selection (`select_lstm_threshold.py`), and evaluation scripts.
- `ml/inference/`: Production inference service (`lstm_inference.py`) and streaming demo (`run_maitri_inference_demo.py`).
- `ml/forecasting/`: Predictive telemetry forecasting modules.
- `ml/tests/`: Pytest test suite.
- `ml/results/`: Evaluation predictions, metrics JSON, confusion matrix plots, threshold search data, reconstruction errors, and inference demo results (`maitri_inference_demo.json`).
