# Sensor ML V2 Hybrid Anomaly Scoring Framework

**Project:** Polarix SIH26060 — Person C (Machine Learning Specialist)
**Experiment:** Step 51 — Hybrid Observation, Transition, and Bounded Drift Scoring
**Status:** `EXPERIMENTAL` (Production Reference Baseline V1 remains strictly frozen)

---

## 1. Motivation & Technical Rationale

Previous empirical investigations (Steps 48–50) established:
1. **Full-Window Sequence MSE (V1):** Suffers from heavy historical window contamination (48.9% of normal windows retain historical anomaly values for 29 steps), inflating false positive rates to >50%.
2. **Instantaneous Last-Step Scoring (Step 50):** Collapses clean-normal false alarms to 1.53% and accurately detects instantaneous `SPIKE` anomalies, but exhibits reduced point-level sensitivity to slow, gradual `DRIFT`.
3. **Deterministic Downstream Classifier:** Successfully isolates flatlines (`STUCK_VALUE`) and sudden changes, which must remain preserved.

The **Hybrid Formulation** combines three complementary normalized signals into a single calibrated scoring vector:
- **Instantaneous Observation Error:** $E_{\text{current}}(t) = (x_t - \hat{x}_t)^2$
- **Transition Step Discrepancy:** $E_{\Delta}(t) = (\Delta x_t - \Delta \hat{x}_t)^2$
- **Bounded Short-Term Drift Signal:** $D_t = |\text{mean}(x_{t-4:t}) - \text{mean}(x_{0:10})|$

---

## 2. Mathematical Formulations

### Component Normalization
Parameters are fitted strictly on **clean-normal validation sequences**:
$$\text{ref}_s = \max(\text{median}(S_{\text{val\_clean}}) + 1.4826 \cdot \text{MAD}(S_{\text{val\_clean}}), 10^{-5})$$

### Hybrid Candidate Variants
- **H1 (Current + Delta):** $S_{H1} = 0.7 \cdot E_{\text{curr\_norm}} + 0.3 \cdot E_{\Delta\text{\_norm}}$
- **H2 (Current + Drift):** $S_{H2} = 0.7 \cdot E_{\text{curr\_norm}} + 0.3 \cdot D_{\text{norm}}$
- **H3 (Current + Delta + Drift):** $S_{H3} = 0.5 \cdot E_{\text{curr\_norm}} + 0.2 \cdot E_{\Delta\text{\_norm}} + 0.3 \cdot D_{\text{norm}}$
- **H4 (Drift-Emphasis):** $S_{H4} = 0.4 \cdot E_{\text{curr\_norm}} + 0.1 \cdot E_{\Delta\text{\_norm}} + 0.5 \cdot D_{\text{norm}}$

---

## 3. Directory Layout

```text
ml/experiments/sensor_v2/hybrid_score/
├── README.md                      # Architectural specification & findings
├── hybrid_scoring_functions.py    # Vectorized signal extraction & normalization routines
├── evaluate_hybrid_scores.py      # Multi-candidate, multi-operating-point evaluation suite
└── results/
    ├── hybrid_score_evaluation.json
    └── hybrid_score_comparison.md
```

---

## 4. Execution

```bash
# Execute hybrid evaluation across Maitri and Bharati
.venv/bin/python ml/experiments/sensor_v2/hybrid_score/evaluate_hybrid_scores.py
```
