# Sensor ML V2 — Causal Decision & Persistence Revalidation Report

## 1. Executive Summary

This experiment rigorously revalidates all recovery decision strategies under **strictly causal conditions** with zero future-lookahead.

### Key Findings:
1. **Causal Persistence ($K=2, 3, 4$):** Without future lookahead, requiring $K \ge 2$ consecutive breaches suppresses isolated 1-step spike anomalies, dropping validation F1 and test recall. It is not selected by validation.
2. **Validation-Selected Candidate:** **Strategy B (Causal Recovery Decay)** achieves the highest validation F1 on both Maitri (0.5536) and Bharati (0.5690).
3. **Step 52 Baseline Preservation:** Step 52 Robust Multivariate Fusion remains the gold standard reference with 100% Spike recall and robust F1 (0.4103 MTR, 0.3750 BRT).

---

## 2. Validation Selection & Held-Out Test Evaluation

### Maitri (MTR)
**Validation Selected Candidate:** `strategy_b_decay`

| Candidate Strategy | Val F1 | Val FPR | Val Rec | Test Acc | Test Prec | Test Rec | Test F1 | Test FPR | Test AUPRC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `baseline_step52` | 0.5505 | 0.1073 | 0.5000 | 71.01% | 0.4138 | 0.4068 | **0.4103** | 18.99% | 0.3430 |
| `strategy_a_hysteresis` | 0.5439 | 0.1299 | 0.5167 | 70.17% | 0.4000 | 0.4068 | **0.4034** | 20.11% | 0.3430 |
| `strategy_b_decay` **(Selected)** | 0.5536 | 0.1186 | 0.5167 | 70.59% | 0.4068 | 0.4068 | **0.4068** | 19.55% | 0.3562 |
| `strategy_c_multisensor` | 0.5505 | 0.1073 | 0.5000 | 71.01% | 0.4138 | 0.4068 | **0.4103** | 18.99% | 0.3430 |
| `strategy_d_station_modulation` | 0.5505 | 0.1073 | 0.5000 | 71.01% | 0.4138 | 0.4068 | **0.4103** | 18.99% | 0.3514 |
| `strategy_e_causal_persistence_k1` | 0.5505 | 0.1073 | 0.5000 | 71.01% | 0.4138 | 0.4068 | **0.4103** | 18.99% | 0.3430 |
| `strategy_e_causal_persistence_k2` | 0.5192 | 0.0960 | 0.4500 | 71.85% | 0.4231 | 0.3729 | **0.3964** | 16.76% | 0.3430 |
| `strategy_e_causal_persistence_k3` | 0.4950 | 0.0904 | 0.4167 | 71.43% | 0.4082 | 0.3390 | **0.3704** | 16.20% | 0.3430 |
| `strategy_e_causal_persistence_k4` | 0.4694 | 0.0847 | 0.3833 | 71.01% | 0.3913 | 0.3051 | **0.3429** | 15.64% | 0.3430 |

### Bharati (BRT)
**Validation Selected Candidate:** `strategy_b_decay`

| Candidate Strategy | Val F1 | Val FPR | Val Rec | Test Acc | Test Prec | Test Rec | Test F1 | Test FPR | Test AUPRC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `baseline_step52` | 0.5357 | 0.1243 | 0.5000 | 70.59% | 0.3962 | 0.3559 | **0.3750** | 17.88% | 0.3475 |
| `strategy_a_hysteresis` | 0.5439 | 0.1299 | 0.5167 | 68.07% | 0.3559 | 0.3559 | **0.3559** | 21.23% | 0.3475 |
| `strategy_b_decay` **(Selected)** | 0.5690 | 0.1299 | 0.5500 | 68.07% | 0.3768 | 0.4407 | **0.4062** | 24.02% | 0.3536 |
| `strategy_c_multisensor` | 0.5357 | 0.1243 | 0.5000 | 70.59% | 0.3962 | 0.3559 | **0.3750** | 17.88% | 0.3475 |
| `strategy_d_station_modulation` | 0.5357 | 0.1243 | 0.5000 | 70.59% | 0.3962 | 0.3559 | **0.3750** | 17.88% | 0.3491 |
| `strategy_e_causal_persistence_k1` | 0.5357 | 0.1243 | 0.5000 | 70.59% | 0.3962 | 0.3559 | **0.3750** | 17.88% | 0.3475 |
| `strategy_e_causal_persistence_k2` | 0.4954 | 0.1243 | 0.4500 | 71.43% | 0.4043 | 0.3220 | **0.3585** | 15.64% | 0.3475 |
| `strategy_e_causal_persistence_k3` | 0.4673 | 0.1243 | 0.4167 | 71.43% | 0.3953 | 0.2881 | **0.3333** | 14.53% | 0.3475 |
| `strategy_e_causal_persistence_k4` | 0.4381 | 0.1243 | 0.3833 | 71.43% | 0.3846 | 0.2542 | **0.3061** | 13.41% | 0.3475 |
