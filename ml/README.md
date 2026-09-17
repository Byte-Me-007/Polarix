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

### Implemented Baselines & Models

#### 1. Maitri Synthetic Telemetry Pipeline
- **Generator**: `ml/data/generate_maitri_dataset.py`
- **Output**: `ml/data/maitri_synthetic_telemetry.csv` (5,000 rows across 5 sensors)
- **Supported Anomaly Types**: `NORMAL`, `SPIKE`, `DRIFT`, `DROPOUT`, `STUCK_VALUE`
- **Sensors**: `TEMP_001` (°C), `PRESS_001` (hPa), `HUM_001` (%), `VIB_001` (mm/s), `POWER_001` (kW)

#### 2. Rolling Z-Score Anomaly Detector (`zscore-v1`)
- **Module**: `ml/training/zscore_detector.py`
- **Evaluation**: `ml/training/evaluate_zscore.py`
- **Methodology**:
  - Independent per-sensor trailing rolling mean and standard deviation.
  - **Leakage Prevention**: Only historical observations up to time $t$ are used; ground truth labels are strictly excluded during scoring.
  - **Dropout Handling**: Missing telemetry (`NaN`) is explicitly identified and classified as `MISSING_DATA` without numerical distortion or interpolation.
  - **Prediction Statuses**: `NORMAL`, `ANOMALY`, `MISSING_DATA`.
  - **Anomaly Score**: Deterministic absolute Z-score $|z|$.
  - **Initial Baseline Threshold**: Configurable threshold (default: `3.0`). *Note: This is an initial heuristic baseline threshold and has NOT yet been formally optimized.*
- **Evaluation Artifacts**:
  - Predictions: `ml/results/zscore_predictions.csv`
  - Metrics: `ml/results/zscore_metrics.json`
  - Visualization: `ml/results/zscore_confusion_matrix.png`

#### 3. Maitri LSTM Autoencoder (`lstm-ae-v1`)
- **Model Definition**: `ml/training/lstm_autoencoder.py`
- **Sequence Preparation**: `ml/training/prepare_sequences.py`
- **Training Pipeline**: `ml/training/train_lstm_autoencoder.py`
- **Purpose**: Sequence-to-sequence deep learning anomaly detector capturing temporal dependencies, multi-step patterns, and subtle contextual deviations.
- **Architecture**:
  - Input dimension: 1 (univariate per sensor)
  - Sequence length: 30 time steps
  - Encoder LSTM: 32 hidden units
  - Latent Bottleneck: 16 units
  - Decoder LSTM: 32 hidden units
  - Output projection: Linear layer reconstructing 30 time steps
- **Training Methodology & Leakage Prevention**:
  - **Chronological Split**: 70% Train, 15% Validation, 15% Test.
  - **Normal-Only Training**: Autoencoder is trained strictly on 100% normal sequences (`is_anomaly == 0`).
  - **Sensor-Specific Normalization**: Mean and standard deviation are calculated strictly from NORMAL training records and saved in `ml/models/lstm-ae-v1_scaler.json`.
  - **Dropout Handling**: Sequences containing missing (`NaN`) values are omitted from model training.
  - **Reconstruction Error**: Computed as per-sample Mean Squared Error $\text{MSE} = \frac{1}{L} \sum_{t=1}^L (x_t - \hat{x}_t)^2$.
  - **Threshold Strategy**: Anomaly thresholding is intentionally deferred to the subsequent validation step. Raw reconstruction errors are preserved in `ml/results/lstm_reconstruction_errors.csv`.
- **Artifacts Saved**:
  - Model Weights: `ml/models/lstm-ae-v1.pt`
  - Config: `ml/models/lstm-ae-v1_config.json`
  - Scalers: `ml/models/lstm-ae-v1_scaler.json`
  - Training History: `ml/results/lstm_training_history.json`
  - Evaluation Reconstruction Errors: `ml/results/lstm_reconstruction_errors.csv`

---

### Planned Future ML Work
- **Threshold Selection**: Formal validation-set threshold optimization (e.g. percentile/F1-optimal threshold tuning).
- **Benchmarking & Model Comparison**: Head-to-head comparison between `zscore-v1` and `lstm-ae-v1` on test set.
- **Inference Interface**: Unified real-time/batch inference service.

---

### Directory Layout
- `ml/data/`: Data storage and synthetic generation scripts (`maitri_synthetic_telemetry.csv`).
- `ml/models/`: Serialized model weights (`lstm-ae-v1.pt`), scalers, and configs.
- `ml/training/`: Training scripts, baseline detectors (`zscore_detector.py`), autoencoder (`lstm_autoencoder.py`, `train_lstm_autoencoder.py`), and evaluation scripts.
- `ml/inference/`: Inference engine and scoring pipelines.
- `ml/forecasting/`: Predictive telemetry forecasting modules.
- `ml/tests/`: Pytest test suite.
- `ml/results/`: Evaluation predictions, metrics JSON, confusion matrix plots, and reconstruction errors.
