# Polarix SIH 2026

## Person C — ML Specialist

### ML Scope
This module is dedicated to machine learning, telemetry anomaly detection, modeling, inference, and ML validation for the Polarix Antarctic Station Monitoring System (SIH26060).

> **Note on Telemetry:** Synthetic telemetry will be used because real Maitri/Bharati historical sensor data is not assumed to be available.

---

### Station Development Rule
- **Maitri** is the first station target.
- **Bharati** will be implemented only after Maitri is completed and validated.

---

### Planned ML Components
- **Z-score baseline**: Statistical baseline anomaly detection.
- **LSTM Autoencoder**: Deep learning sequence-based anomaly detection.
- **Anomaly scoring**: Continuous error and anomaly scoring algorithms.
- **Threshold selection**: Calibrated threshold selection methods (e.g. dynamic/static thresholds).
- **Evaluation Metrics**:
  - Precision / Recall / F1
  - Confusion matrix
- **Model versioning**: Versioned model artifact tracking and storage.
- **ML inference interface**: Clean interface for real-time and batch telemetry evaluation.
- **ML-only tests**: Automated testing suite for ML pipelines, scoring, and inference.

---

### Directory Layout
- `ml/data/`: Data storage for synthetic training, validation, and test datasets.
- `ml/models/`: Serialized model weights, scalers, and metadata.
- `ml/training/`: Training scripts and hyperparameter configurations.
- `ml/inference/`: Inference engine and scoring pipelines.
- `ml/forecasting/`: Predictive telemetry forecasting modules.
- `ml/tests/`: Pytest suite for ML components.
- `ml/results/`: Evaluation results, metrics reports, and performance plots.
