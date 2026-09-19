# Sensor ML V2 — Final Causal State-Machine Decision Layer

## 1. Problem Formulation & Objective

This module implements a causally valid, deterministic state-machine decision layer to govern station-level anomaly decisions during post-anomaly recovery windows without sacrificing isolated single-step anomaly detection (such as temperature spikes, vibration surges, or stuck sensor flatlines).

---

## 2. State-Machine Architecture & Invariants

```
       INITIAL
          ↓
       NORMAL (Clean / Stable Normal)
          ↓ (Score >= Threshold OR Multi-Sensor Corroborated OR Physical Deviation > Bound)
    ACTIVE_ANOMALY
          ↓ (Telemetry returned to Baseline AND Score Decaying)
       RECOVERY
```

### Supported Candidates Evaluated:
1. **Candidate A (Reference):** Raw Step 52 Robust Multivariate Threshold ($S(t) \ge T_{\text{base}}$).
2. **Candidate B (Recovery Suppression):** Strict recovery barrier ($1.35 \times T_{\text{base}}$) applied during recovery window ($\Delta t \le 30$).
3. **Candidate C (Suppression + Strong Override):** Recovery suppression with overrides for strong isolated spikes ($S(t) \ge 1.50 \cdot T_{\text{base}}$), multi-sensor co-elevation ($N_{\text{elev}} \ge 2$), and physical deviation ($|Z| > 2.0$).
4. **Candidate D (Decay + Strong Override):** Causal recovery decay with strong isolated overrides.

---

## 3. Explicit Safety & Causality Invariants

1. **Strict Causality:** Decisions at step $t$ depend solely on telemetry observations up to step $t$.
2. **Future Independence:** Modifying future observations at steps $> t$ produces zero change in predictions at steps $\le t$.
3. **Isolated Anomaly Protection:** Single-step spikes are never suppressed when physical deviation or score breaches strong thresholds.
4. **Classifier Integrity:** Deterministic categorization (`SPIKE`, `DRIFT`, `STUCK_VALUE`, `MISSING_DATA`) remains authoritative.
5. **Idempotency:** Re-processing identical timestamps does not falsely advance the causal state.
6. **Missing Data Handling:** Emits `MISSING_DATA` state without triggering false alarms.

---

## 4. Authoritative Experimental Reference

**Step 52 Robust Multivariate Fusion** remains the authoritative experimental reference for production planning ($F1 = 0.4103$ MTR, $0.3750$ BRT, 100% Spike recall, 0.0% clean-normal FPR).
