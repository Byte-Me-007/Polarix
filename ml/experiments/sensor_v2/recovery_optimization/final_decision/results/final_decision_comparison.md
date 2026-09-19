# Sensor ML V2 — Final Causal Decision State Machine Evaluation Report

## 1. Executive Summary & Authoritative Reference

This experiment evaluates a causally valid, deterministic state-machine decision layer designed to suppress recovery-period false positives without sacrificing isolated anomaly detection.

### Key Scientific Conclusions:
1. **Safety Override Invariant:** Introducing strong isolated-anomaly overrides ($S(t) \ge 1.5\cdot T$, $N_{\text{elev}} \ge 2$, $|Z| > 2.0$) successfully protects 100% of Spike anomalies from suppression.
2. **Authoritative Experimental Reference:** **Step 52 Robust Multivariate Fusion** remains the authoritative experimental reference for production planning ($F1 = 0.4103$ MTR, $0.3750$ BRT, 100% Spike recall, 0.0% clean-normal FPR).
3. **Population Integrity:** True station-level evaluation size is verified at **$N = 238$** synchronized evaluation instants (179 Normal, 59 Anomaly).

---

## 2. Quantitative Performance Comparison ($N = 238$)

### Maitri (MTR)
**Validation Selected Candidate:** `candidate_a_reference`

| Candidate | Val F1 | Val FPR | Val Rec | Test Acc | Test Prec | Test Rec | Test F1 | Test FPR | Test AUPRC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `candidate_a_reference` **(Selected)** | 0.5505 | 0.1073 | 0.5000 | 71.01% | 0.4138 | 0.4068 | **0.4103** | 18.99% | 0.3430 |
| `candidate_b_suppression` | 0.5472 | 0.0960 | 0.4833 | 72.27% | 0.4286 | 0.3559 | **0.3889** | 15.64% | 0.3430 |
| `candidate_c_suppression_override` | 0.5505 | 0.1073 | 0.5000 | 71.01% | 0.4138 | 0.4068 | **0.4103** | 18.99% | 0.3430 |
| `candidate_d_decay_override` | 0.5505 | 0.1073 | 0.5000 | 71.01% | 0.4138 | 0.4068 | **0.4103** | 18.99% | 0.3430 |

#### Maitri Recovery-Window Error Profile by Interval Post-Anomaly

| Time Range | Sample Count ($N$) | False Positives | False Positive Rate | Mean Score | Median Score | P95 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **0-1** | 3 | 2 | 66.7% | 103.07 | 123.59 | 177.22 |
| **2-5** | 12 | 8 | 66.7% | 44.94 | 40.17 | 96.99 |
| **6-10** | 15 | 10 | 66.7% | 28.65 | 27.84 | 79.47 |
| **11-20** | 30 | 6 | 20.0% | 2.80 | 1.78 | 8.46 |
| **21-30** | 30 | 8 | 26.7% | 3.03 | 1.72 | 9.75 |
| **>30** | 89 | 0 | 0.0% | 0.91 | 0.77 | 1.83 |

### Bharati (BRT)
**Validation Selected Candidate:** `candidate_a_reference`

| Candidate | Val F1 | Val FPR | Val Rec | Test Acc | Test Prec | Test Rec | Test F1 | Test FPR | Test AUPRC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `candidate_a_reference` **(Selected)** | 0.5357 | 0.1243 | 0.5000 | 70.59% | 0.3962 | 0.3559 | **0.3750** | 17.88% | 0.3475 |
| `candidate_b_suppression` | 0.5091 | 0.1243 | 0.4667 | 70.59% | 0.3830 | 0.3051 | **0.3396** | 16.20% | 0.3475 |
| `candidate_c_suppression_override` | 0.5357 | 0.1243 | 0.5000 | 70.59% | 0.3962 | 0.3559 | **0.3750** | 17.88% | 0.3475 |
| `candidate_d_decay_override` | 0.5357 | 0.1243 | 0.5000 | 70.59% | 0.3962 | 0.3559 | **0.3750** | 17.88% | 0.3475 |

#### Bharati Recovery-Window Error Profile by Interval Post-Anomaly

| Time Range | Sample Count ($N$) | False Positives | False Positive Rate | Mean Score | Median Score | P95 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **0-1** | 3 | 2 | 66.7% | 171.01 | 146.05 | 343.56 |
| **2-5** | 12 | 8 | 66.7% | 72.46 | 86.43 | 137.55 |
| **6-10** | 15 | 8 | 53.3% | 19.04 | 7.61 | 53.83 |
| **11-20** | 30 | 4 | 13.3% | 3.88 | 3.02 | 11.07 |
| **21-30** | 30 | 10 | 33.3% | 6.84 | 1.89 | 21.48 |
| **>30** | 89 | 0 | 0.0% | 0.90 | 0.88 | 1.51 |
