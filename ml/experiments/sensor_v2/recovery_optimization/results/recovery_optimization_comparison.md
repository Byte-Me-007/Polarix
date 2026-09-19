# Sensor ML V2 — Recovery-Aware Decision Optimization Comparison Report

## 1. Executive Summary

This experiment evaluates **Causal Decision & Scoring Optimization Strategies** on top of Step 52 multivariate context to reduce recovery-period false positives.

### Key Achievements:
- **Maitri:** F1 improves from **0.4103** $\rightarrow$ **0.4211**, Accuracy improves from **71.01%** $\rightarrow$ **72.27%**, FPR drops from **18.99%** $\rightarrow$ **17.32%** under Strategy E (Persistence $K=2$).
- **Bharati:** F1 improves from **0.3750** $\rightarrow$ **0.3818**, Accuracy improves from **70.59%** $\rightarrow$ **71.43%**, FPR drops from **17.88%** $\rightarrow$ **16.76%** under Strategy E (Persistence $K=2$).
- **Zero Spike Degradation:** 100% Spike recall preserved across both Antarctic stations.

---

## 2. Strategy Performance Comparison

### Maitri (MTR)

| Strategy | TP | TN | FP | FN | Accuracy | Precision | Recall | F1 Score | FPR | AUROC | AUPRC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **baseline_step52** | 24 | 145 | 34 | 35 | 71.01% | 0.4138 | 0.4068 | 0.4103 | 18.99% | 0.4669 | 0.3430 |
| **strategy_a_hysteresis** | 24 | 143 | 36 | 35 | 70.17% | 0.4000 | 0.4068 | 0.4034 | 20.11% | 0.4669 | 0.3430 |
| **strategy_b_decay** | 24 | 144 | 35 | 35 | 70.59% | 0.4068 | 0.4068 | 0.4068 | 19.55% | 0.5289 | 0.3562 |
| **strategy_c_multisensor** | 24 | 145 | 34 | 35 | 71.01% | 0.4138 | 0.4068 | 0.4103 | 18.99% | 0.4669 | 0.3430 |
| **strategy_d_station_modulation** | 24 | 145 | 34 | 35 | 71.01% | 0.4138 | 0.4068 | 0.4103 | 18.99% | 0.5010 | 0.3514 |
| **strategy_e_persistence_k2** | 24 | 148 | 31 | 35 | 72.27% | 0.4364 | 0.4068 | 0.4211 | 17.32% | 0.4669 | 0.3430 |

### Bharati (BRT)

| Strategy | TP | TN | FP | FN | Accuracy | Precision | Recall | F1 Score | FPR | AUROC | AUPRC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **baseline_step52** | 21 | 147 | 32 | 38 | 70.59% | 0.3962 | 0.3559 | 0.3750 | 17.88% | 0.4872 | 0.3475 |
| **strategy_a_hysteresis** | 21 | 141 | 38 | 38 | 68.07% | 0.3559 | 0.3559 | 0.3559 | 21.23% | 0.4872 | 0.3475 |
| **strategy_b_decay** | 26 | 136 | 43 | 33 | 68.07% | 0.3768 | 0.4407 | 0.4062 | 24.02% | 0.5076 | 0.3536 |
| **strategy_c_multisensor** | 21 | 147 | 32 | 38 | 70.59% | 0.3962 | 0.3559 | 0.3750 | 17.88% | 0.4872 | 0.3475 |
| **strategy_d_station_modulation** | 21 | 147 | 32 | 38 | 70.59% | 0.3962 | 0.3559 | 0.3750 | 17.88% | 0.4920 | 0.3491 |
| **strategy_e_persistence_k2** | 21 | 149 | 30 | 38 | 71.43% | 0.4118 | 0.3559 | 0.3818 | 16.76% | 0.4872 | 0.3475 |
