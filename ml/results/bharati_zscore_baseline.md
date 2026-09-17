# Polarix Bharati Z-Score Baseline Report (SIH26060 - Person C)

**Station:** Bharati (`BRT`)  
**Model Version:** `zscore-bharati-v1`  
**Baseline Parameters:** Rolling Window = `30`, Threshold = `3.0` (± 3.0 sigma)  
**Status:** Initial Statistical Baseline  

---

> [!IMPORTANT]
> **SYNTHETIC DATA DISCLAIMER**:
> All evaluations are conducted strictly on synthetic telemetry generated for Bharati station.
> No real Antarctic sensor telemetry was used. These metrics reflect statistical properties on synthetic workloads and do NOT constitute field deployment readiness or certified operational performance.

---

## 1. Overview & Baseline Purpose

The Rolling Z-Score detector (`zscore-bharati-v1`) serves as the classical univariate statistical baseline for Bharati station anomaly detection. It maintains an independent trailing 30-step history per sensor to compute standard score deviations ($z = (x - \mu) / \sigma$).

This statistical baseline provides a reference benchmark against which the subsequent Bharati LSTM Autoencoder (`lstm-ae-bharati-v1`) will be evaluated.

---

## 2. Quantitative Performance Across Splits

### Test Split Evaluation (1,500 records / 15% partition):
- **True Positives (TP)**: `43`
- **True Negatives (TN)**: `1166`
- **False Positives (FP)**: `17`
- **False Negatives (FN)**: `274`
- **Accuracy**: `80.60%`
- **Precision**: `0.7167`
- **Recall**: `0.1356`
- **F1-Score**: `0.2281`
- **False Positive Rate (FPR)**: `1.44%`

### Validation Split Evaluation (1,500 records / 15% partition):
- **Accuracy**: `80.13%` | **Precision**: `0.6825` | **Recall**: `0.1340` | **F1-Score**: `0.2240`

---

## 3. Anomaly-Type Detection Analysis (Test Split)

| Anomaly Type | Total Injected | Detected by Z-Score | Recall Rate | Operational Behavioral Analysis |
| :--- | :--- | :--- | :--- | :--- |
| **`SPIKE`** | `19` | `10` | **`10/19 (52.63%)`** | High sensitivity to abrupt high-magnitude excursions exceeding 3 sigma. |
| **`DRIFT`** | `150` | `5` | **`5/150 (3.33%)`** | Low sensitivity because the trailing rolling mean dynamically shifts with the gradual ramp. |
| **`STUCK_VALUE`** | `120` | `0` | **`0/120 (0.00%)`** | Flatlines within normal sensor range do not deviate from local mean. |
| **`DROPOUT`** | `28` | `28` | **`28/28 (100.00%)`** | Handled explicitly via missing-data ingestion rule (`MISSING_DATA`). |

---

## 4. Key Findings & Baseline Limitations

1. **High Precision / Low False Alarms**: The $3.0\sigma$ threshold achieves low false alarm rates (1.44% FPR) and high precision (0.7167).
2. **Drift Blindspot**: Due to rolling mean adaptation, univariate Z-score detectors fail to detect gradual monotonic drift (5/150 (3.33%) recall), motivating the need for sequence-aware LSTM Autoencoders.
3. **Flatline Insensitivity**: Single-threshold Z-score cannot detect frozen sensors without dedicated rolling variance features.
4. **Initial Uncalibrated Baseline**: Threshold `3.0` is an initial heuristic baseline and has not been tuned or optimized.
