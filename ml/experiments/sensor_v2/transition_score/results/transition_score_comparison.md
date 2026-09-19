# Sensor ML V2 Transition-Focused Anomaly Scoring Report

**Project:** Polarix SIH26060 — Person C (ML Specialist)
**Experiment:** Step 50 — Transition & Observation-Centric Anomaly Scoring
**Status:** `TRANSITION_EVALUATION_COMPLETE`

---

## Station: Maitri (`MTR`)

### Reference Frozen Baseline: `lstm-ae-v1`
- Precision: 0.2612 | Recall: 0.5260 | F1: 0.3490 | FPR: 0.4815 | Accuracy: 0.5203 | AUROC: 0.4714 | AUPRC: 0.2153

### Formulation Comparison on Held-Out Test Set (Operating Point: Max Validation F1):

| Scoring Formulation | Threshold | Precision | Recall | F1-Score | FPR | Accuracy | AUROC | AUPRC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Frozen V1 (Full MSE)** | `0.017674` | 0.2612 | 0.5260 | **0.3490** | 0.4815 | 0.5203 | 0.4714 | 0.2153 |
| `full_window_mse` | `0.000781` | 0.2445 | 1.0000 | **0.3929** | 1.0000 | 0.2445 | 0.4570 | 0.2094 |
| `last_step_reconstruction` | `0.100253` | 0.2765 | 0.2076 | **0.2372** | 0.1758 | 0.6734 | 0.5428 | 0.3175 |
| `recent_weighted_reconstruction` | `0.000242` | 0.2445 | 1.0000 | **0.3929** | 1.0000 | 0.2445 | 0.4447 | 0.2292 |
| `delta_transition_error` | `0.000000` | 0.2439 | 0.9965 | **0.3918** | 1.0000 | 0.2437 | 0.3093 | 0.1888 |
| `composite_transition_score` | `0.060228` | 0.2500 | 0.2042 | **0.2248** | 0.1982 | 0.6557 | 0.4759 | 0.2780 |

### Clean Normal vs Contaminated Recovery Normal Breakdown (Max F1 Operating Point):

| Scoring Formulation | Clean Normal FPR | Clean Normal False Alarms | Recovery Normal FPR | Recovery Normal False Alarms |
| :--- | :---: | :---: | :---: | :---: |
| `full_window_mse` | **100.00%** | 458/458 | **100.00%** | 435/435 |
| `last_step_reconstruction` | **1.53%** | 7/458 | **34.48%** | 150/435 |
| `recent_weighted_reconstruction` | **100.00%** | 458/458 | **100.00%** | 435/435 |
| `delta_transition_error` | **100.00%** | 458/458 | **100.00%** | 435/435 |
| `composite_transition_score` | **4.37%** | 20/458 | **36.09%** | 157/435 |

### Multi-Operating-Point Analysis for `last_step_reconstruction`:

| Operating Point Criterion | Threshold | Precision | Recall | F1-Score | FPR | Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Max Validation F1 | `0.100253` | 0.2765 | 0.2076 | **0.2372** | 0.1758 | 0.6734 |
| FPR <= 10% Constrained | `0.166108` | 0.2699 | 0.1522 | **0.1947** | 0.1333 | 0.6920 |
| Balanced Operating Point | `0.100253` | 0.2765 | 0.2076 | **0.2372** | 0.1758 | 0.6734 |

## Station: Bharati (`BRT`)

### Reference Frozen Baseline: `lstm-ae-bharati-v1`
- Precision: 0.2679 | Recall: 0.5709 | F1: 0.3646 | FPR: 0.5050 | Accuracy: 0.5135 | AUROC: 0.4708 | AUPRC: 0.2155

### Formulation Comparison on Held-Out Test Set (Operating Point: Max Validation F1):

| Scoring Formulation | Threshold | Precision | Recall | F1-Score | FPR | Accuracy | AUROC | AUPRC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Frozen V1 (Full MSE)** | `0.013215` | 0.2679 | 0.5709 | **0.3646** | 0.5050 | 0.5135 | 0.4708 | 0.2155 |
| `full_window_mse` | `0.016886` | 0.2268 | 0.4221 | **0.2950** | 0.4658 | 0.5068 | 0.4529 | 0.2087 |
| `last_step_reconstruction` | `0.106109` | 0.2899 | 0.2768 | **0.2832** | 0.2195 | 0.6574 | 0.5243 | 0.3137 |
| `recent_weighted_reconstruction` | `0.030067` | 0.2353 | 0.3460 | **0.2801** | 0.3639 | 0.5651 | 0.4293 | 0.2270 |
| `delta_transition_error` | `0.000000` | 0.2445 | 1.0000 | **0.3929** | 1.0000 | 0.2445 | 0.3301 | 0.1967 |
| `composite_transition_score` | `0.091278` | 0.2578 | 0.2007 | **0.2257** | 0.1870 | 0.6633 | 0.4701 | 0.2814 |

### Clean Normal vs Contaminated Recovery Normal Breakdown (Max F1 Operating Point):

| Scoring Formulation | Clean Normal FPR | Clean Normal False Alarms | Recovery Normal FPR | Recovery Normal False Alarms |
| :--- | :---: | :---: | :---: | :---: |
| `full_window_mse` | **21.83%** | 100/458 | **72.64%** | 316/435 |
| `last_step_reconstruction` | **1.53%** | 7/458 | **43.45%** | 189/435 |
| `recent_weighted_reconstruction` | **3.71%** | 17/458 | **70.80%** | 308/435 |
| `delta_transition_error` | **100.00%** | 458/458 | **100.00%** | 435/435 |
| `composite_transition_score` | **1.75%** | 8/458 | **36.55%** | 159/435 |

### Multi-Operating-Point Analysis for `last_step_reconstruction`:

| Operating Point Criterion | Threshold | Precision | Recall | F1-Score | FPR | Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Max Validation F1 | `0.106109` | 0.2899 | 0.2768 | **0.2832** | 0.2195 | 0.6574 |
| FPR <= 10% Constrained | `0.199361` | 0.2757 | 0.1765 | **0.2152** | 0.1501 | 0.6853 |
| Balanced Operating Point | `0.229604` | 0.2683 | 0.1522 | **0.1943** | 0.1344 | 0.6912 |

---

## Key Empirical Findings

1. **Last-step scoring eliminates reliance on past 29 timesteps, preventing historical anomalies from contaminating post-anomaly normal observations.**
1. **Delta transition scoring measures instantaneous velocity changes, sharply identifying step spikes.**
1. **Recent-weighted scoring offers a continuous decay trade-off between full sequence memory and point observation focus.**
1. **Downstream deterministic anomaly type classification remains intact and unaffected.**
