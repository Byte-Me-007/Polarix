# Polarix STUCK_VALUE / Flatline Anomaly Detection Investigation & Classifier Refinement Report

**Project:** Polarix — Smart India Hackathon 2026  
**Problem Statement:** SIH26060  
**Team:** Byte Me_26 (Team ID: 143760)  
**Role:** Person C — Machine Learning Specialist  
**Stations:** Bharati (`BRT`) & Maitri (`MTR`)  
**Scope:** Deterministic downstream STUCK_VALUE anomaly classification analysis and rule refinement  
**Status:** `INVESTIGATION_COMPLETE_CLASSIFIER_STRENGTHENED`  
**Date:** 2026-09-18  

---

## 1. Executive Summary & Original Limitation

In previous evaluations, static flatline (`STUCK_VALUE`) telemetry was identified as an inherent structural challenge for sequence-based neural autoencoders:
- **LSTM Reconstruction Limitation**: Neural autoencoders reproduce flatline / constant vectors $[c, c, \dots, c]$ with near-zero MSE reconstruction loss ($< 10^{-4}$), causing unshifted flatlines to yield primary detector status `NORMAL`.
- **Hybrid Division of Labor**: In the Polarix hybrid ML architecture, primary LSTM reconstruction scoring captures dynamic trajectory and amplitude distortions, while the deterministic downstream heuristic classifier identifies physical archetypes (Spikes, Drifts, and Stuck Values).
- **Previous Downstream Classifier Gap**: The initial classifier rule evaluated `max_consecutive_near_stuck >= 12` across the entire 30-step window. Consequently, if a sensor was frozen at steps $0 \dots 14$ but recovered to active physical variation at steps $15 \dots 29$, the classifier erroneously reported `STUCK_VALUE` for the active tail observation.

This investigation refines the downstream deterministic classifier to enforce **active tail flatline detection**, eliminating recovery false alarms while preserving $100\%$ detection of genuine sensor freezes.

---

## 2. Root Cause & Mathematical Analysis

### A. Why Autoencoders Reconstruct Flatlines with Near-Zero Error
For an autoencoder $f_\theta: \mathbb{R}^{30} \rightarrow \mathbb{R}^{30}$, an input consisting of constant scalar $c$:
$$\mathbf{x} = [c, c, \dots, c]^T$$
passes through hidden recurrent layers with zero step-to-step activation delta. The reconstructed vector $\hat{\mathbf{x}} \approx \mathbf{x}$, resulting in:
$$\text{MSE}(\mathbf{x}, \hat{\mathbf{x}}) \approx 0 \ll \text{Threshold}$$

### B. Distinguishing Active Sensor Freeze from Historical Recovery
In streaming sliding-window telemetry at time $t$ (tail observation $\mathbf{x}_{29}$):
1. **Active Freeze**: The sensor is currently stuck at time $t$ if the tail run length of near-identical consecutive readings is $\ge 8$ steps ($\Delta x_i \le 10^{-4}$), or the 10-step tail variance is $\le 10^{-4}$.
2. **Historical Recovery**: If a sensor flatlined 20 minutes ago but is actively oscillating in the last 10 minutes, the historical flatline exists in the 30-step FIFO buffer, but the current observation $\mathbf{x}_{29}$ is **healthy and active**.

---

## 3. Refined Classifier Rule Specification

The deterministic physical classification rule in `BharatiAnomalyTypeClassifier` and `AnomalyTypeClassifier` was strengthened as follows:

```python
# Active flatline at tail or across entire window
is_tail_stuck = feats.tail_consecutive_stuck >= self.stuck_run_threshold
is_near_frozen_tail = (feats.tail_std_10 <= self.stuck_tolerance and feats.tail_consecutive_stuck >= 6)
is_entirely_flat = (feats.std <= self.stuck_tolerance and feats.max_consecutive_near_stuck >= 20)

if is_tail_stuck or is_near_frozen_tail or is_entirely_flat:
    return "STUCK_VALUE"
```

### Feature Definitions:
- `tail_consecutive_stuck`: Number of consecutive identical / near-identical observations ($\le 10^{-4}$ delta) immediately ending at `arr[-1]`.
- `tail_std_10`: Sample standard deviation over the last 10 observations.
- `stuck_run_threshold`: Minimum run length of 8 consecutive flat points to confirm a sustained physical fault.
- `stuck_tolerance`: $10^{-4}$ numerical threshold accounting for floating-point quantization.

---

## 4. Synthetic Benchmark Validation Results

The refined classifier was rigorously evaluated across 11 targeted synthetic telemetry scenarios:

| Scenario ID | Test Condition | Input Description | Expected Class | Classifier Output | Verification Verdict |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **1** | Normal Telemetry | Diurnal sinusoidal cycle + Gaussian noise ($\sigma=0.10$) | `NORMAL` | `NORMAL` | **PASS** |
| **2** | Short Stable Period | Natural temporary dwell (3-4 identical points) | `NORMAL` | `NORMAL` | **PASS** |
| **3** | Genuine STUCK_VALUE | Active flatline of 10 points at sequence tail | `STUCK_VALUE` | `STUCK_VALUE` | **PASS** |
| **4** | Long Exact Flatline | Full 30-observation constant sequence | `STUCK_VALUE` | `STUCK_VALUE` | **PASS** |
| **5** | Near-Flatline | 30-step flatline with micro-jitter ($\sigma=10^{-5}$) | `STUCK_VALUE` | `STUCK_VALUE` | **PASS** |
| **6** | Spike Anomaly | Sharp instantaneous step impulse | `SPIKE` | `SPIKE` | **PASS** |
| **7** | Drift Anomaly | Monotonic directional ramp divergence | `DRIFT` | `DRIFT` | **PASS** |
| **8** | Dropout / Missing | Telemetry window containing `NaN` / Non-finite | `MISSING_DATA`| `MISSING_DATA`| **PASS** |
| **9** | Recovery After Stuck | Stuck at $0 \dots 14$, active sinusoidal at $15 \dots 29$ | `NORMAL` | `NORMAL` | **PASS** |
| **10**| Multi-Sensor Isolation | 5 Bharati sensors evaluated independently | `STUCK_VALUE` | `STUCK_VALUE` | **PASS** |
| **11**| Determinism Check | 100 repeated evaluations on identical sequence | `STUCK_VALUE` | `STUCK_VALUE` | **PASS** |

### Benchmark Metrics:
- **STUCK_VALUE Precision**: `1.00`
- **STUCK_VALUE Recall**: `1.00`
- **Recovery False Alarm Rate**: `0.00` (Zero false stuck alarms on recovered sensors).

---

## 5. Architectural Integrity & Frozen Model Baseline

- **Frozen LSTM Models Untouched**: `lstm-ae-bharati-v1.pt`, `lstm-ae-v1.pt`, scalers, configs, and decision thresholds remain 100% untouched and cryptographically verified against their SHA-256 digests.
- **Contract & Status Semantics Preserved**: Primary detector status (`NORMAL`, `ANOMALY`, `INSUFFICIENT_DATA`, `MISSING_DATA`) and anomaly types (`NORMAL`, `SPIKE`, `DRIFT`, `STUCK_VALUE`, `UNKNOWN`) remain strictly aligned with the canonical ML contract.

---

## 6. Technical Limitations

1. **Synthetic Validation**: All scenarios evaluated on synthetic data generated for SIH 2026.
2. **Tolerance Bounds**: Flatlines with high-frequency noise greater than $10^{-4}$ require drift or spike classification depending on trajectory shape.
3. **Prototype Scope**: Designed for hackathon integration and demonstration without claims of physical Antarctic mission certification.
