# Sensor ML V2 Multivariate Sensor-Context Fusion Framework

**Project:** Polarix SIH26060 — Person C (Machine Learning Specialist)
**Experiment:** Step 52 — Multivariate Sensor-Context Fusion
**Status:** `EXPERIMENTAL` (Baseline V1 remains strictly frozen)

---

## 1. Motivation & Architectural Foundation

Previous steps (Steps 48–51) demonstrated that:
1. **Univariate Isolation:** Treating each sensor independently ignores cross-channel correlations and physical couplings (e.g. ambient temperature drops impacting station heating power consumption and humidity).
2. **Station-Level Fusion:** Evaluating multi-sensor context across all 5 synchronized station telemetry channels (`TEMP`, `PRESS`, `HUM`, `VIB`, `POWER`) enables high-confidence station-level anomaly risk estimation.

```text
Raw Multi-Channel Telemetry (5 Sensors Aligned Chronologically)
        │
        ▼
Per-Sensor Temporal Anomaly Autoencoder + Transition Discrepancy
        │
        ▼
Robust Scaled Sensor Anomaly Signals & Health Vectors
        │
        ▼
Multivariate Context Fusion Engine (Max, Agreement, Robust Aggregate)
        │
        ▼
Station-Level Anomaly Risk & Operational Context
        │
        ▼
Downstream Multi-Agent Forecasting & Decision Support
```

---

## 2. Fusion Strategies Evaluated

- **MV1 — Max Sensor Context:** $S_{\text{MV1}}(t) = \max_{s \in \text{valid}} S_{\text{norm}, s}(t)$
- **MV2 — Mean Sensor Context:** $S_{\text{MV2}}(t) = \frac{1}{|\text{valid}|} \sum_{s \in \text{valid}} S_{\text{norm}, s}(t)$
- **MV3 — Robust Aggregate:** $S_{\text{MV3}}(t) = \text{median}(S_{\text{norm}}) + 0.5 \cdot \text{IQR}(S_{\text{norm}})$
- **MV4 — Agreement-Aware:** $S_{\text{MV4}}(t) = S_{\text{max}} \cdot (1 + 0.5 \cdot \frac{N_{\text{elevated}}}{|\text{valid}|})$
- **MV5 — Hybrid Context:** $S_{\text{MV5}}(t) = 0.7 \cdot S_{\text{max}} + 0.3 \cdot S_{\text{rest\_mean}}$

---

## 3. Directory Layout

```text
ml/experiments/sensor_v2/multivariate_context/
├── README.md                           # Architectural specification & findings
├── multivariate_scoring_functions.py   # Timestamp alignment & multi-sensor fusion logic
├── evaluate_multivariate_context.py    # Multi-strategy evaluation pipeline
└── results/
    ├── multivariate_context_evaluation.json
    └── multivariate_context_comparison.md
```

---

## 4. Execution

```bash
# Run multivariate context evaluation across Maitri and Bharati
.venv/bin/python ml/experiments/sensor_v2/multivariate_context/evaluate_multivariate_context.py
```
