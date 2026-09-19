# Sensor ML V2 — Causal Recovery Decision Optimization & Persistence Revalidation

## 1. Executive Context & Baseline Terminology

To maintain strict scientific and evaluation integrity across Sensor ML iterations, the model lineage and labels are defined as follows:

1. **Original Frozen V1 Baseline (Production Reference):**
   - Maitri: `lstm-ae-v1.pt` (F1 = 0.3490, FPR = 0.4815, Recall = 0.5260, Precision = 0.2612, AUPRC = 0.2153)
   - Bharati: `lstm-ae-bharati-v1.pt` (F1 = 0.3646, FPR = 0.5050, Recall = 0.5709, Precision = 0.2679, AUPRC = 0.2155)
2. **V2 Raw Global Candidate (Step 47):** 60-epoch raw reconstruction MSE (F1 = 0.3937 MTR / 0.3093 BRT, FPR = 0.9966 MTR / 0.5028 BRT).
3. **V2 H3 Hybrid Candidate (Step 51):** Multi-component normalized formulation combining current observation, delta transition, and drift ($H3$).
4. **V2 Recovery-Aware Multivariate Candidate (Step 52):** Robust station-level cross-sensor aggregation across all 5 telemetry channels (F1 = 0.4103 MTR / 0.3750 BRT, Clean-Normal FPR = 0.0%, AUPRC = 0.3430 MTR / 0.3475 BRT).
5. **Step 53 Exploratory Strategies:** Initial exploration of hysteresis, decay, and persistence.
6. **Step 54 Causal Decision & Persistence Revalidation:** Strictly causal revalidation removing future lookahead.

---

## 2. Strictly Causal Persistence Semantics

A causal $K$-consecutive persistence detector operates with zero lookahead:
$$\text{prediction}[t] = \begin{cases} 1 & \text{if } \sum_{i=0}^{K-1} \mathbb{I}(S(t-i) \ge T) = K \\ 0 & \text{otherwise} \end{cases}$$

### Empirical Revalidation Findings:
- Under strictly causal implementation, requiring $K \ge 2$ consecutive breaches suppresses isolated single-step spike anomalies, dropping validation recall ($0.5000 \rightarrow 0.4500$) and test recall ($0.4068 \rightarrow 0.3729$ MTR).
- Consequently, **$K \ge 2$ persistence is NOT selected by validation** because single-step spikes require immediate alert generation.
- **Strategy B (Causal Recovery Decay)** achieves the highest validation F1 on both Maitri ($F1 = 0.5536$) and Bharati ($F1 = 0.5690$).

---

## 3. Station Population & Sample Count Reconciliation

- **Station-Level Population ($N = 238$):** The true evaluation set size for station-level multivariate decisions, consisting of 238 synchronized chronological timestamps where all 5 station sensors are simultaneously observed (179 Normal, 59 Anomaly).
- **Per-Channel Concatenated Population ($N = 1,182$):** The sum of individual univariate sequence windows across all 5 separate sensor channels ($~236.4$ windows per channel).
