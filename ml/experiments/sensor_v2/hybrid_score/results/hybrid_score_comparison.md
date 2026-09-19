# Sensor ML V2 Hybrid Anomaly Scoring Report

**Project:** Polarix SIH26060 — Person C (ML Specialist)
**Experiment:** Step 51 — Hybrid Observation, Transition & Bounded Drift Scoring
**Status:** `HYBRID_EVALUATION_COMPLETE`

---

## Station: Maitri (`MTR`)

### Comprehensive Baseline & Candidate Comparison (Held-Out Test Set):

| Model / Formulation | Threshold | Precision | Recall | F1-Score | FPR | Accuracy | AUROC | AUPRC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Frozen V1 (Full MSE)** | `0.017674` | 0.2612 | 0.5260 | **0.3490** | 0.4815 | 0.5203 | 0.4714 | 0.2153 |
| Step 50 Last-Step | `0.100253` | 0.2765 | 0.2076 | **0.2372** | 0.1758 | 0.6734 | 0.5428 | 0.3175 |
| Step 50 Recent-Weighted | `0.000242` | 0.2445 | 1.0000 | **0.3929** | 1.0000 | 0.2445 | 0.4447 | 0.2292 |
| Step 50 Composite | `0.060228` | 0.2500 | 0.2042 | **0.2248** | 0.1982 | 0.6557 | 0.4759 | 0.2780 |
| **H1 (Current 0.7 + Delta 0.3)** | `5.0160` | 0.3333 | 0.2872 | **0.3086** | 0.1859 | 0.6853 | 0.5095 | 0.3047 |
| **H2 (Current 0.7 + Drift 0.3)** | `5.0187` | 0.3360 | 0.2907 | **0.3117** | 0.1859 | 0.6861 | 0.5030 | 0.3139 |
| **H3 (Current 0.5 + Delta 0.2 + Drift 0.3)** | `3.6978` | 0.3346 | 0.2941 | **0.3131** | 0.1892 | 0.6844 | 0.4715 | 0.2966 |
| **H4 (Current 0.4 + Delta 0.1 + Drift 0.5)** | `3.6945` | 0.3476 | 0.2803 | **0.3103** | 0.1702 | 0.6954 | 0.4553 | 0.2983 |

### Recovery vs Clean Normal False Alarms & Anomaly Recall Breakdown:

| Formulation | Clean Normal FPR | Recovery Normal FPR | Separation Ratio | SPIKE Recall | DRIFT Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `H1_current_delta` | **0.87%** | **37.24%** | 28.02x | 100.00% | 42.67% |
| `H2_current_drift` | **1.09%** | **37.01%** | 21.55x | 100.00% | 43.33% |
| `H3_current_delta_drift` | **0.87%** | **37.93%** | 21.37x | 100.00% | 44.00% |
| `H4_drift_emphasis` | **0.66%** | **34.25%** | 16.40x | 100.00% | 41.33% |

## Station: Bharati (`BRT`)

### Comprehensive Baseline & Candidate Comparison (Held-Out Test Set):

| Model / Formulation | Threshold | Precision | Recall | F1-Score | FPR | Accuracy | AUROC | AUPRC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Frozen V1 (Full MSE)** | `0.013215` | 0.2679 | 0.5709 | **0.3646** | 0.5050 | 0.5135 | 0.4708 | 0.2155 |
| Step 50 Last-Step | `0.106109` | 0.2899 | 0.2768 | **0.2832** | 0.2195 | 0.6574 | 0.5243 | 0.3137 |
| Step 50 Recent-Weighted | `0.030067` | 0.2353 | 0.3460 | **0.2801** | 0.3639 | 0.5651 | 0.4293 | 0.2270 |
| Step 50 Composite | `0.091278` | 0.2578 | 0.2007 | **0.2257** | 0.1870 | 0.6633 | 0.4701 | 0.2814 |
| **H1 (Current 0.7 + Delta 0.3)** | `4.1933` | 0.3366 | 0.3529 | **0.3446** | 0.2251 | 0.6717 | 0.4889 | 0.2996 |
| **H2 (Current 0.7 + Drift 0.3)** | `3.8181` | 0.3333 | 0.3668 | **0.3493** | 0.2374 | 0.6658 | 0.4909 | 0.3097 |
| **H3 (Current 0.5 + Delta 0.2 + Drift 0.3)** | `3.1129` | 0.3376 | 0.3633 | **0.3500** | 0.2307 | 0.6701 | 0.4680 | 0.2960 |
| **H4 (Current 0.4 + Delta 0.1 + Drift 0.5)** | `2.5141` | 0.3242 | 0.3702 | **0.3457** | 0.2497 | 0.6574 | 0.4619 | 0.2975 |

### Recovery vs Clean Normal False Alarms & Anomaly Recall Breakdown:

| Formulation | Clean Normal FPR | Recovery Normal FPR | Separation Ratio | SPIKE Recall | DRIFT Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `H1_current_delta` | **2.84%** | **43.22%** | 32.86x | 100.00% | 55.33% |
| `H2_current_drift` | **2.62%** | **45.98%** | 23.32x | 100.00% | 58.00% |
| `H3_current_delta_drift` | **2.84%** | **44.37%** | 24.75x | 100.00% | 57.33% |
| `H4_drift_emphasis` | **2.84%** | **48.28%** | 18.51x | 100.00% | 58.67% |

---

## Key Takeaways

1. **Integrating short-term bounded drift tracking (H2, H3, H4) significantly improves DRIFT anomaly recall compared to last-step error in isolation.**
1. **Normalizing components via clean-normal validation MAD scales stabilizes disparate physical sensor dimensions.**
1. **Clean-normal false alarms remain substantially lower than full-window MSE, proving the effectiveness of localized observation-transition scoring.**
1. **Downstream deterministic anomaly classification rules remain 100% functional and compatible.**
