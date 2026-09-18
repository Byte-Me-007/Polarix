# Sensor ML V2 Retraining & Calibration Framework

**Project:** Polarix (Smart India Hackathon 2026 — Problem Statement SIH26060)  
**Author:** Byte Me_26 — PERSON C (Machine Learning Specialist)  
**Status:** `EXPERIMENTAL / CANDIDATE ONLY` (Reference Baseline V1 remains frozen)

---

## 1. Objective & Purpose

The Sensor ML V2 experiment framework investigates whether improved deep learning training procedures and systematic threshold calibration can improve telemetry reconstruction and anomaly detection performance across the Indian Antarctic research stations **Maitri (`MTR`)** and **Bharati (`BRT`)**.

### Key Rules & Invariants
- **Frozen V1 Baseline:** The production V1 models (`lstm-ae-v1` and `lstm-ae-bharati-v1`), their configuration JSONs, scalers, decision thresholds, and SHA-256 hashes are **strictly frozen and unmodified**.
- **Experimental Separation:** All V2 training artifacts, weights, loss histories, and reports reside strictly within `ml/experiments/sensor_v2/` and are tagged `CANDIDATE`.
- **Validation-Only Calibration:** Decision thresholds are selected **exclusively on validation data** (never on the held-out test split) to prevent data leakage.
- **Realistic Reporting:** Training autoencoders longer lowers reconstruction error on normal data, but does not guarantee higher anomaly F1 scores; metrics are evaluated honestly without manufactured targets.

---

## 2. Downstream Polarix ML Architecture

Sensor ML is the foundational telemetry ingestion and signal health layer in the multi-tiered Polarix Digital Twin:

```text
Raw Sensor Telemetry Streams (Maitri & Bharati)
        │
        ▼
Per-Sensor Anomaly ML (LSTM Autoencoder + Deterministic Classifier)
        │
        ▼
Anomaly Score / Status / Type + Sensor Health Metrics
        │
        ▼
Multivariate Feature Fusion (Cross-Channel Correlation)
        │
        ▼
Subsystem Forecasting Models (Energy, Battery, Temperature, Logistics)
        │
        ▼
Station Operational Risk Engine (Maitri & Bharati Health Indices)
        │
        ▼
Operational Decision & Digital Twin Visualization Layer
```

---

## 3. V2 Training Improvements

| Feature | V1 Production Baseline | V2 Retraining Candidate |
| :--- | :--- | :--- |
| **Max Epoch Budget** | 30 epochs | **60 epochs** |
| **LR Scheduler** | None (Static LR = 0.001) | **ReduceLROnPlateau** (factor=0.5, patience=4, min_lr=1e-5) |
| **Early Stopping** | Patience = 7 | **Patience = 12** |
| **Checkpointing** | Final / Best Epoch | **Best Validation Loss Checkpoint** |
| **Reproducibility** | Seed = 42 | **Seed = 42** (Torch, NumPy, Python) |
| **Architecture** | 1-Layer LSTM AE (hidden=32, latent=16) | **Preserved (Isolates training effect)** |

---

## 4. Experiment Structure

```text
ml/experiments/sensor_v2/
├── config.py                     # V2 experiment configurations (Maitri & Bharati)
├── train_v2_models.py            # Retraining pipeline with LR scheduler & checkpointing
├── evaluate_v2_experiments.py    # Validation threshold tuning & held-out test evaluation
├── run_v2_experiments.py         # Unified CLI experiment runner
├── README.md                     # Documentation & architectural specification
├── models/                       # V2 candidate model weights, scalers, and configs
│   ├── lstm-ae-v2-candidate.pt
│   ├── lstm-ae-v2-candidate_config.json
│   ├── lstm-ae-v2-candidate_scaler.json
│   ├── lstm-ae-bharati-v2-candidate.pt
│   ├── lstm-ae-bharati-v2-candidate_config.json
│   └── lstm-ae-bharati-v2-candidate_scaler.json
└── results/                      # V2 loss histories, reconstruction errors, and comparison reports
    ├── mtr_v2_training_history.json
    ├── brt_v2_training_history.json
    ├── mtr_v2_threshold.json
    ├── brt_v2_threshold.json
    ├── mtr_v2_reconstruction_errors.csv
    ├── brt_v2_reconstruction_errors.csv
    ├── sensor_v2_comparison.json
    └── sensor_v2_comparison.md
```

---

## 5. Execution Commands

To execute the complete V2 training and evaluation pipeline:

```bash
# Run complete experiment suite:
.venv/bin/python ml/experiments/sensor_v2/run_v2_experiments.py

# Or run individual stages:
.venv/bin/python ml/experiments/sensor_v2/train_v2_models.py
.venv/bin/python ml/experiments/sensor_v2/evaluate_v2_experiments.py
```
