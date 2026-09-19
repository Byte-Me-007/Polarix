# Polarix Energy Deficit-Risk Prediction Report (SIH26060)

**Model Version:** `energy-deficit-risk-v1`
**Operating Decision Threshold:** `tau = 0.3500` (Frozen from validation tuning)
**Evaluation Partition:** Held-Out Chronological Test Partition (`2026-11-07T06:00:00Z` $\to$ `2026-12-31T23:00:00Z`, $N=1,314$ hours/station)
**Author:** Person C — Machine Learning Specialist
**Evaluation Date:** 2026-09-19

---

## 1. Executive Summary & Problem Formulation

Energy Deficit-Risk prediction models the probability that an Antarctic research station microgrid will enter a critical deficit condition in the next hour ($t \to t+1\,\text{h}$):
$$\text{Deficit Condition} \iff (\text{SoC}(t+1) < 25.0\%) \lor (P_{\text{demand}}(t+1) > 0.95 \cdot P_{\text{generator, rated}})$$

### Class Distribution Across Chronological Splits:
- **Maitri (`MTR`):** Train $156$ positives ($2.54\%$) | Val $49$ positives ($3.73\%$) | Test $27$ positives ($2.05\%$)
- **Bharati (`BRT`):** Train $76$ positives ($1.24\%$) | Val $18$ positives ($1.37\%$) | Test $23$ positives ($1.75\%$)
- **Combined:** Train $232$ positives ($1.89\%$) | Val $67$ positives ($2.55\%$) | Test $50$ positives ($1.90\%$)

---

## 2. Comparative Model Benchmark (Combined Test Partition, N=2626)

| Model Architecture | Accuracy | Precision | Recall | F1 Score | Specificity | Balanced Acc | ROC-AUC | PR-AUC | Missed Deficits |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Gradient Boosting V1 (Selected)** | **$99.81\%$** | **$92.45\%$** | **$98.00\%$** | **$0.9515$** | **$0.9984$** | **$0.9892$** | **$0.9998$** | **$0.9921$** | **$1 (2.0\%)$** |
| **Logistic Regression (Balanced)** | $98.17\%$ | $51.02\%$ | $100.00\%$ | $0.6757$ | $0.9814$ | $0.9907$ | $0.9986$ | $0.9465$ | $0 ($0.0\%)$ |
| **Rule-Based Persistence** | $98.71\%$ | $61.11\%$ | $88.00\%$ | $0.7213$ | $0.9891$ | $0.9346$ | $0.9346$ | $0.5401$ | $6 ($12.0\%)$ |
| **Majority Class Baseline** | $98.10\%$ | $0.00\%$ | $0.00\%$ | $0.0000$ | $1.0000$ | $0.5000$ | $0.5000$ | $0.0190$ | $50 ($100.0\%)$ |

---

## 3. Station-Specific Performance

### 3.1 Maitri (`MTR`) — Inland Microgrid (N=1313, Positives=27)
- **Gradient Boosting:** Accuracy: $99.77\%$, Precision: $92.86\%$, Recall: $96.30\%$, F1: $0.9455$, Specificity: $0.9984$
- **Confusion Matrix:** TN=1284, FP=2, FN=1, TP=26
- **False Negatives:** 1 (Missed Deficit Rate: 3.70%)

### 3.2 Bharati (`BRT`) — Coastal Microgrid (N=1313, Positives=23)
- **Gradient Boosting:** Accuracy: $99.85\%$, Precision: $92.00\%$, Recall: $100.00\%$, F1: $0.9583$, Specificity: $0.9984$
- **Confusion Matrix:** TN=1288, FP=2, FN=0, TP=23
- **False Negatives:** 0 (Missed Deficit Rate: 0.00%)

---

## 4. Exploratory Cross-Station Transfer Generalization

Transfer experiments evaluate model portability when trained strictly on one station and tested on the other:

| Transfer Direction | Training Station | Evaluation Station | Test Accuracy | Precision | Recall | F1 Score | Specificity | ROC-AUC | PR-AUC |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **MTR $\to$ BRT Transfer** | Maitri (Inland, $120\,\text{kW}$) | Bharati (Coastal, $150\,\text{kW}$) | $97.33\%$ | $38.89\%$ | $91.30\%$ | $0.5455$ | $0.9744$ | $0.9932$ | $0.8050$ |
| **BRT $\to$ MTR Transfer** | Bharati (Coastal, $150\,\text{kW}$) | Maitri (Inland, $120\,\text{kW}$) | $99.77\%$ | $100.00\%$ | $88.89\%$ | $0.9412$ | $1.0000$ | $0.9992$ | $0.9759$ |

---

## 5. Limitations & Governance Disclaimer

> [!CAUTION]
> **Safety Disclaimer:**
> This model provides an advisory machine learning probability signal and **must not** be used as an autonomous control cutoff without supervisory microgrid engineering rules. Telemetry is calibrated from synthetic Polarix operational data.
