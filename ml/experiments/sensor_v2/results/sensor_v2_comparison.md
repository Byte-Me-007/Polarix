# Sensor ML V2 Retraining & Calibration Comparison Report

**Project:** Polarix SIH26060 — Person C (Machine Learning Specialist)  
**Experiment:** Sensor ML V2 Candidate Retraining  
**Status:** `EXPERIMENT_COMPLETE__V1_FROZEN_PRESERVED`  

---

## 1. Executive Summary & Metric Comparison

This report compares the **Frozen V1 Reference Baseline** against the **V2 Retraining Candidate** across both Antarctic stations.

### Station: Maitri (`MTR`)

| Metric | V1 Reference Baseline | V2 Candidate | Delta (V2 - V1) |
| :--- | :---: | :---: | :---: |
| **Model Version** | `lstm-ae-v1` | `lstm-ae-v2-candidate` | — |
| **Decision Threshold** | `0.017674` | `0.000722` | `-0.016952` |
| **F1-Score** | **0.3490** | **0.3937** | **+0.0447** |
| **Precision** | 0.2612 | 0.2451 | -0.0160 |
| **Recall** | 0.5260 | 1.0000 | +0.4740 |
| **False Positive Rate (FPR)** | 0.4815 | 0.9966 | +0.5151 |
| **Accuracy** | 0.5203 | 0.2470 | -0.2733 |
| **AUROC** | 0.4714 | 0.4422 | -0.0292 |
| **AUPRC** | 0.2153 | 0.2045 | -0.0108 |

#### Test Confusion Matrix (V2 Candidate):
- **True Positives (TP):** 289
- **True Negatives (TN):** 3
- **False Positives (FP):** 890
- **False Negatives (FN):** 0

#### Per-Anomaly-Type Detection Breakdown (V2 Candidate):
- **DRIFT:** 150 / 150 detected (Recall: 100.00%)
- **NORMAL:** 890 false alarms / 893 nominals (FPR: 99.66%)
- **SPIKE:** 19 / 19 detected (Recall: 100.00%)
- **STUCK_VALUE:** 120 / 120 detected (Recall: 100.00%)

### Station: Bharati (`BRT`)

| Metric | V1 Reference Baseline | V2 Candidate | Delta (V2 - V1) |
| :--- | :---: | :---: | :---: |
| **Model Version** | `lstm-ae-bharati-v1` | `lstm-ae-bharati-v2-candidate` | — |
| **Decision Threshold** | `0.013215` | `0.013013` | `-0.000202` |
| **F1-Score** | **0.3646** | **0.3093** | **-0.0553** |
| **Precision** | 0.2679 | 0.2312 | -0.0367 |
| **Recall** | 0.5709 | 0.4671 | -0.1038 |
| **False Positive Rate (FPR)** | 0.5050 | 0.5028 | -0.0022 |
| **Accuracy** | 0.5135 | 0.4898 | -0.0237 |
| **AUROC** | 0.4708 | 0.4525 | -0.0183 |
| **AUPRC** | 0.2155 | 0.2079 | -0.0076 |

#### Test Confusion Matrix (V2 Candidate):
- **True Positives (TP):** 135
- **True Negatives (TN):** 444
- **False Positives (FP):** 449
- **False Negatives (FN):** 154

#### Per-Anomaly-Type Detection Breakdown (V2 Candidate):
- **DRIFT:** 104 / 150 detected (Recall: 69.33%)
- **NORMAL:** 449 false alarms / 893 nominals (FPR: 50.28%)
- **SPIKE:** 19 / 19 detected (Recall: 100.00%)
- **STUCK_VALUE:** 12 / 120 detected (Recall: 10.00%)

---

## 2. Downstream Multi-Agent Architecture

Sensor ML V2 candidates form the foundational sensor telemetry layer in the Polarix hierarchical ML ecosystem:

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

## 3. Conclusions & Key Findings

1. **Extended epoch training with ReduceLROnPlateau converges to a lower reconstruction loss on normal sequences.**
1. **Threshold selection on validation data prevents test set leakage.**
1. **Reconstruction loss alone does not eliminate diurnal false alarms; deterministic anomaly-type classification remains essential.**
1. **V1 baseline artifacts remain untouched, frozen, and authoritative for production.**
1. **V2 models are preserved as candidates under ml/experiments/sensor_v2/.**
