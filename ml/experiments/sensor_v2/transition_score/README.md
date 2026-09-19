# Sensor ML V2 Transition & Observation-Centric Scoring Framework

**Project:** Polarix SIH26060 — Person C (Machine Learning Specialist)
**Experiment:** Step 50 — Transition-Focused Anomaly Scoring Formulation
**Status:** `EXPERIMENTAL` (Baseline V1 remains strictly frozen)

---

## 1. Motivation & Problem Formulation

In Step 48 and Step 49, empirical diagnosis demonstrated that the standard 30-step LSTM Autoencoder mean reconstruction error suffers from **window contamination lag**:
- When an anomaly event ends, the subsequent 29 time steps are ground-truth nominal (`is_anomaly = 0`), but their 30-step input sequence fed into the autoencoder still retains past anomalous values.
- As a result, calculating anomaly error across all 30 steps produces severe false alarms during recovery (72.87% FPR on recovery windows).

### Scoring Formulations Evaluated

1. **Last-Step Reconstruction Error:**
   $$\text{score}_{\text{last}} = (x_t - \hat{x}_t)^2$$
   Measures reconstruction discrepancy strictly at the current/final timestep $t$, discarding historical reconstruction error.

2. **Recent-Weighted Reconstruction Error:**
   $$\text{score}_{\text{recent}} = \sum_{k=0}^{L-1} w_k (x_{t-L+1+k} - \hat{x}_{t-L+1+k})^2, \quad w_k = \frac{\exp(\alpha k)}{\sum_{j=0}^{L-1}\exp(\alpha j)}$$
   Weights recent observations exponentially higher ($\alpha = 0.15$), smoothing the transition while prioritizing the present.

3. **Delta Transition Error:**
   $$\Delta x = x_t - x_{t-1}, \quad \Delta \hat{x} = \hat{x}_t - \hat{x}_{t-1}$$
   $$\text{score}_{\text{delta}} = (\Delta x - \Delta \hat{x})^2$$
   Measures step-to-step velocity deviations rather than absolute magnitude.

4. **Composite Transition-Observation Error:**
   $$\text{score}_{\text{composite}} = 0.5 \cdot \text{score}_{\text{last}} + 0.5 \cdot \text{score}_{\text{delta}}$$
   Balances observation magnitude error with dynamic step change velocity.

---

## 2. Directory Layout

```text
ml/experiments/sensor_v2/transition_score/
├── README.md                          # Architectural specification and findings
├── scoring_functions.py               # Vectorized scoring formulation definitions
├── evaluate_transition_scores.py      # Multi-station, multi-criterion evaluation pipeline
└── results/                           # Evaluation reports and comparisons
    ├── transition_score_evaluation.json
    └── transition_score_comparison.md
```

---

## 3. Usage & Execution

```bash
# Run transition scoring evaluation across Maitri and Bharati
.venv/bin/python ml/experiments/sensor_v2/transition_score/evaluate_transition_scores.py
```
