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

### Implemented Baselines & Components

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

---

### Planned Future ML Work
- **LSTM Autoencoder**: Sequence-to-sequence reconstruction architecture for contextual and multi-step anomalies.
- **Threshold Selection**: Formal validation-set threshold optimization (precision/recall trade-off).
- **Benchmarking & Model Comparison**: Comprehensive evaluation comparing Z-score against LSTM Autoencoder.

---

### Directory Layout
- `ml/data/`: Data storage and synthetic generation scripts (`maitri_synthetic_telemetry.csv`).
- `ml/models/`: Serialized model weights, scalers, and metadata.
- `ml/training/`: Training scripts, baseline detectors (`zscore_detector.py`), and evaluation (`evaluate_zscore.py`).
- `ml/inference/`: Inference engine and scoring pipelines.
- `ml/forecasting/`: Predictive telemetry forecasting modules.
- `ml/tests/`: Pytest test suite.
- `ml/results/`: Evaluation predictions, metrics JSON, and confusion matrix plots.
