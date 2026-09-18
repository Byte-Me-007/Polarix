# Bharati LSTM Autoencoder False-Positive Rate Investigation & Performance Optimization Report

**Project:** Polarix — Smart India Hackathon 2026  
**Problem Statement:** SIH26060  
**Team:** Byte Me_26 (Team ID: 143760)  
**Author:** Person C — Machine Learning Specialist  
**Station:** Bharati (`BRT`)  
**Frozen Model Baseline:** `lstm-ae-bharati-v1` (Frozen Threshold: `0.013215307652775843`)  
**Investigation Focus:** Empirical root-cause analysis of high FPR (50.50% test set) and evaluation of candidate per-sensor calibration strategies  
**Status:** `ANALYSIS_COMPLETE_V1_FROZEN`  
**Date:** 2026-09-18  

---

## 1. Problem Statement

During comprehensive evaluation (Step 26 & Step 35), the frozen Bharati LSTM autoencoder (`lstm-ae-bharati-v1`) achieved high anomaly recall (57.09% on test, detecting 100% of Spikes and 88.0% of Drifts) but exhibited a substantial false-positive rate:
- **Test FPR:** `50.50%` (451 false alarms out of 893 normal observations).
- **Test Precision:** `0.2679`.
- **Test F1:** `0.3646`.

This investigation performs a controlled, evidence-based empirical analysis to diagnose the exact statistical and structural causes of the high false-positive rate and evaluate candidate calibration strategies strictly using the validation split.

The Polarix ML pipeline is hybrid: LSTM reconstruction scoring provides anomaly detection/scoring, deterministic downstream classification identifies anomaly types where supported, and explicit missing-data handling covers dropout/offline telemetry.

---

## 2. V1 Baseline Metrics Summary

The authoritative, cryptographically frozen Bharati V1 artifacts remain untouched:

| Metric Category | Validation Split (`val`) | Held-Out Test Split (`test`) |
| :--- | :---: | :---: |
| **True Positives (TP)** | 184 | 165 |
| **True Negatives (TN)** | 449 | 442 |
| **False Positives (FP)** | 440 | 451 |
| **False Negatives (FN)** | 108 | 124 |
| **Accuracy** | 53.60% | 51.35% |
| **Precision** | 0.2949 | 0.2679 |
| **Recall** | 0.6301 | 0.5709 |
| **F1 Score** | 0.4017 | 0.3646 |
| **False Positive Rate (FPR)** | **49.49%** | **50.50%** |

---

## 3. Reconstruction Error Distribution Analysis

To determine why normal observations produce high reconstruction errors, we decomposed normal validation observations into two distinct populations:
1. **Clean Normal (`any_anomaly_in_window == 0`)**: Sequences containing 30 purely normal observations with zero anomaly contamination in history.
2. **Trailing Normal (`is_anomaly == 0` but `any_anomaly_in_window == 1`)**: Observations where the current point is normal, but the 30-observation rolling sequence still contains anomaly points from the preceding 29 steps.

### Empirical Distribution Breakdown (Validation Split):

| Sub-Population | Sample Count ($N$) | Mean MSE | Median MSE | 75th Percentile | Max MSE |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Clean Normal** | 454 | `0.012086` | `0.009266` | `0.013580` | `0.057099` |
| **Trailing Window Normal** | 435 | `0.945401` | `0.576371` | `1.464679` | `3.892249` |
| **True Anomalies** | 292 | `0.211976` | `0.024255` | `0.180295` | `3.036366` |

### Key Diagnostic Insight:
- **Trailing Window Recovery Lag**: Trailing normal points have an average reconstruction error **78x higher** than clean normal points (`0.9454` vs `0.0121`). Because the autoencoder reconstructs the full 30-point sequence, an anomaly lingering in the history causes high reconstruction loss for 29 steps after physical recovery.

---

## 4. Sensor-Level Disparity Analysis

Examining clean normal errors per sensor revealed severe baseline reconstruction disparities:

| Sensor ID | Clean Normal Median | Clean Normal P99 | All Normal Median | V1 Global Threshold | V1 Test FPR |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`BRT_PRESS_001`** | `0.004080` | `0.007511` | `0.005523` | `0.013215` | 32.95% |
| **`BRT_TEMP_001`** | `0.004622` | `0.011469` | `0.005324` | `0.013215` | 32.22% |
| **`BRT_POWER_001`** | `0.008183` | `0.013899` | `0.010001` | `0.013215` | 42.70% |
| **`BRT_HUM_001`** | `0.012737` | `0.019745` | `0.014264` | `0.013215` | 45.25% |
| **`BRT_VIB_001`** | `0.028379` | `0.054121` | `0.030635` | `0.013215` | **98.89%** |

### Why a Single Global Threshold Fails:
- For **`BRT_VIB_001`**, the global threshold (`0.013215`) is **far below** its clean normal median (`0.028379`). Consequently, **98.89% of normal vibration points** were flagged as anomalous under V1.
- Conversely, for **`BRT_PRESS_001`**, `0.013215` is almost double the clean 99th percentile, leading to an unbalanced sensitivity distribution.

---

## 5. Validation Threshold Strategy Experiments

We evaluated multiple candidate threshold strategies strictly on the **Validation Split** (`val`):

### Strategy Overview:
- **Strategy A (Baseline V1 Global)**: Global threshold `0.013215307652775843`.
- **Strategy B1 (Global Max F1)**: Global search optimizing F1 on validation $\rightarrow T = 0.013676$.
- **Strategy B2 (Global Low FPR)**: Global search with FPR $\le 10\% \rightarrow T = 1.880222$.
- **Strategy C1 (Per-Sensor Unconstrained Max F1)**: Independent threshold per sensor maximizing validation F1.
- **Strategy C2 (Per-Sensor P99 Clean Normal)**: Independent threshold per sensor set to the 99th percentile of clean normal validation error.
- **Strategy C3 (Per-Sensor Constrained Max F1, FPR $\le 35\%$)**: Independent threshold per sensor maximizing F1 subject to per-sensor FPR $\le 35\%$ on validation.

---

## 6. Candidate Configurations Summary

| Strategy ID | Threshold Type | Sensor Thresholds (`HUM`, `POWER`, `PRESS`, `TEMP`, `VIB`) | Optimization Goal |
| :--- | :--- | :--- | :--- |
| **Strategy A** | Global | All = `0.013215` | V1 Baseline |
| **Strategy B1** | Global | All = `0.013676` | Global Max F1 |
| **Strategy B2** | Global | All = `1.880222` | Global Low FPR ($\le 10\%$) |
| **Strategy C1** | Per-Sensor | `0.017251`, `0.012973`, `0.007412`, `0.001830`, `0.033881` | Per-Sensor Max F1 |
| **Strategy C2** | Per-Sensor | `0.019745`, `0.013899`, `0.007511`, `0.011469`, `0.054121` | P99 Clean Normal |
| **Candidate C3** | Per-Sensor | `0.017266`, `0.013177`, `0.007405`, `0.012522`, `0.050735` | Constrained Max F1 ($\text{FPR} \le 35\%$) |

---

## 7. Validation Split Comparison

| Strategy | TP | TN | FP | FN | Accuracy | Precision | Recall | F1 Score | FPR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Strategy A (V1 Global)** | 184 | 449 | 440 | 108 | 53.60% | 0.2949 | 0.6301 | 0.4017 | 49.49% |
| **Strategy B1 (Global Max F1)** | 183 | 454 | 435 | 109 | 53.94% | 0.2961 | 0.6267 | 0.4022 | 48.93% |
| **Strategy B2 (Global Low FPR)** | 7 | 802 | 87 | 285 | 68.50% | 0.0745 | 0.0240 | 0.0363 | 9.79% |
| **Strategy C1 (Per-Sensor Max F1)** | 192 | 472 | 417 | 100 | 56.22% | 0.3153 | 0.6575 | 0.4262 | 46.91% |
| **Strategy C2 (P99 Clean Normal)** | 155 | 594 | 295 | 137 | 63.42% | 0.3444 | 0.5308 | 0.4178 | 33.18% |
| **Candidate C3 (Constrained Max F1)** | **159** | **588** | **301** | **133** | **63.25%** | **0.3457** | **0.5445** | **0.4229** | **33.86%** |

### Validation Verdict:
- **Candidate C3** achieved the strongest balanced tradeoff on validation: reducing false positives by **139 observations** ($\text{FPR } 49.49\% \rightarrow 33.86\%$), increasing precision from **0.2949 to 0.3457**, while retaining **54.45% recall** and improving overall F1 to **0.4229**.

---

## 8. Final Unbiased Test Evaluation

Following strict ML best practices, **Candidate C3** was frozen on validation and evaluated on the untouched held-out **Test Split**:

| Metric | Frozen Baseline V1 | Candidate C3 (Per-Sensor) | Net Change ($\Delta$) | Tradeoff Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **True Positives (TP)** | 165 | 144 | -21 | Moderate recall reduction on weak drift tails |
| **True Negatives (TN)** | 442 | 541 | +99 | **99 false alarms successfully eliminated** |
| **False Positives (FP)** | 451 | 352 | -99 | **22.0% absolute reduction in false positives** |
| **False Negatives (FN)** | 124 | 145 | +21 | Preserved 100% of Spike anomalies |
| **Accuracy** | 51.35% | **57.95%** | **+6.60%** | Clear improvement in overall classification |
| **Precision** | 0.2679 | **0.2903** | **+0.0224** | Higher positive predictive value |
| **Recall** | 0.5709 | 0.4983 | -0.0726 | Balanced operating point |
| **F1 Score** | 0.3646 | **0.3669** | **+0.0023** | F1 slightly improved |
| **False Positive Rate (FPR)** | **50.50%** | **39.42%** | **-11.08%** | **Substantial reduction in FPR** |

### Sensor-Level Test Breakdown (V1 vs C3):

| Sensor ID | V1 False Positives | V1 FPR | C3 False Positives | C3 FPR | C3 Precision | C3 Recall |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `BRT_HUM_001` | 81 | 45.25% | **64** | **35.75%** | 0.2727 | 0.4211 |
| `BRT_POWER_001` | 76 | 42.70% | **76** | **42.70%** | 0.3153 | 0.5932 |
| `BRT_PRESS_001` | 58 | 32.95% | **84** | **47.73%** | 0.2759 | 0.5517 |
| `BRT_TEMP_001` | 58 | 32.22% | **58** | **32.22%** | 0.3256 | 0.4912 |
| `BRT_VIB_001` | 178 | 98.89% | **70** | **38.89%** | 0.2632 | 0.4310 |

> **Major Breakthrough on Vibration**: For `BRT_VIB_001`, False Positives collapsed from **178 down to 70** (FPR down from **98.89% to 38.89%**), eliminating 108 false alarms on vibration alone.

---

## 9. Error Breakdown & Trailing Window Artifacts

Decomposing the remaining 352 test false positives under Candidate C3 reveals:

```
Total Test False Positives: 352
 ├── Clean Normal False Positives:     25  (7.1% of FPs, Clean FPR = 5.46%)
 └── Trailing Window False Positives: 327 (92.9% of FPs, Trailing FPR = 75.17%)
```

- **Clean FPR is only 5.46%**: When sensors operate in truly normal stationary conditions, Candidate C3 achieves a low 5.46% false alarm rate.
- **Trailing Window Effect**: 92.9% of remaining false positives occur during the 29 time steps immediately following an anomaly event while the buffer clears.

### Anomaly Type Recall & Hybrid Pipeline Analysis:
- **`SPIKE`** ($N=19$): **100.0% Recall** (19/19 detected in both V1 and C3).
- **`DRIFT`** ($N=150$): **83.33% Recall** (125/150 detected in C3 vs 132/150 in V1).
- **`STUCK_VALUE`** ($N=120$): **0.0% Recall via LSTM Reconstruction Loss alone** (Reconstruction loss alone does not detect flatlines; handled by the downstream deterministic physical classifier).
- **Hybrid Pipeline Summary**: The LSTM autoencoder provides dynamic temporal reconstruction scoring; the downstream heuristic layer classifies physical patterns (Spike, Drift, Stuck Value); and structural telemetry handling catches missing/dropout data.

---

## 10. Technical Limitations & Scope

1. **Synthetic Telemetry**: Analysis is conducted exclusively on synthetic datasets generated for SIH 2026.
2. **Point-in-Time Evaluation Metric**: Standard sequence-to-point labeling inherently penalizes sliding window models during the 29-step post-anomaly recovery buffer.
3. **No Field Production Claims**: Performance figures represent academic prototype benchmarking, not certified Antarctic deployment accuracy.
4. **Empirical Evaluation**: The Candidate C3 result represents an empirical evaluation on the available synthetic partitions, not a mathematical proof or guaranteed operational bounds.

---

## 11. Recommendation & Architectural Status

### Status of Frozen V1:
- **`lstm-ae-bharati-v1` remains the authoritative, cryptographically frozen model** for Polarix integration. Its weights, scaler, config, and threshold (`0.013215307652775843`) remain 100% untouched.

### Candidate C3 Status:
- **Candidate C3 is an empirically validated candidate calibration strategy on the available synthetic validation/test splits** that reduces test FPR from 50.50% to 39.42% and slashes clean normal FPR to 5.46%.
- It is cataloged in `ml/results/bharati_lstm_performance_analysis.json` as a reference candidate for future multi-sensor threshold upgrades and is **NOT** integrated into the frozen v1 production path.
