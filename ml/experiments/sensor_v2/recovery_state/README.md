# Sensor ML V2 — Causal Recovery-State Detection Experiment

## 1. Overview & Problem Formulation

The previous Sensor ML V2 experiments (Steps 48–52) confirmed a fundamental limitation in univariate temporal autoencoders:
When an anomaly (e.g. temperature spike, power surge, or vibration pulse) ends, the physical telemetry value immediately returns to its clean normal operating baseline. However, because the LSTM autoencoder operates on a rolling window of 30 historical timesteps, the window remains contaminated by the preceding anomaly for up to 30 subsequent steps.

This historical sequence contamination causes elevated reconstruction error and false alarms during the **recovery window** ($t_{\text{steps\_since\_anomaly}} \in [1, 30]$), leading to recovery-normal false-positive rates of ~38%.

### Core Hypothesis
A current observation should be treated differently when its physical telemetry value is returning toward its clean-normal baseline after an anomaly, even if historical points inside the temporal window remain contaminated.

---

## 2. State Machine Architecture

```
        INITIAL / UNKNOWN
               ↓
          CLEAN_NORMAL
               ↓ (Score > Threshold AND Z > Bound)
         ACTIVE_ANOMALY
               ↓ (Z <= Bound AND Score Decaying)
            RECOVERY
               ↓ (Steps > W_recovery OR Stable for K steps)
          STABLE_NORMAL
```

### Supported Inferred States:
1. `CLEAN_NORMAL`: Standard stationary normal telemetry without recent anomalies.
2. `ACTIVE_ANOMALY`: Current telemetry and score breach anomaly criteria.
3. `RECOVERY`: Telemetry is within recovery window ($1 \le \Delta t \le 30$) following an anomaly, but the current observation has returned to within normal baseline bounds ($Z_t \le Z_{\text{bound}}$) and score is decaying.
4. `STABLE_NORMAL`: Post-recovery sequence verified normal for $K \ge 5$ consecutive steps.
5. `INSUFFICIENT_CONTEXT`: Fewer than 3 historical timesteps available.
6. `MISSING_DATA`: Telemetry is null or NaN.

---

## 3. Causal Feature Extraction

At each timestamp $t$, the detector computes features using **only** current and historical data:

1. $\Delta t_{\text{anom}}$ (`steps_since_last_anomaly`): Elapsed steps since last detected anomaly trigger.
2. $N_{\text{anom}, 30}$ (`recent_anomaly_count_w30`): Count of anomaly triggers in the rolling 30-step window.
3. $D_{\text{anom}}$ (`recent_anomaly_duration`): Duration of the most recent continuous anomaly run.
4. $S(t)$ (`current_score`): Base hybrid anomaly score at step $t$.
5. $S(t-1)$ (`prev_score`): Base hybrid anomaly score at step $t-1$.
6. $\Delta S(t)$ (`score_decay_rate`): Score slope $S(t) - S(t-1)$.
7. $Z_t$ (`baseline_z_deviation`): Normalized deviation from clean-normal baseline $|x_t - \mu_{\text{clean}}| / \sigma_{\text{clean}}$.
8. $M_t$ (`movement_toward_baseline`): $Z_{t-1} - Z_t$ (positive indicates convergence toward baseline).
9. $\text{Var}_{5}(Z)$ (`recent_local_variance`): Variance of the last 5 normalized deviations.

---

## 4. Recovery Attenuation Scoring

In `RECOVERY` state, when $Z_t \le Z_{\text{bound}}$ and $\Delta S(t) \le \epsilon_{\text{decay}}$:

$$\alpha(t) = \max\left(0.10, \min\left(1.0, \frac{Z_t}{Z_{\text{bound}}} \times 0.70\right)\right)$$

$$S_{\text{recovery\_aware}}(t) = S_{\text{base}}(t) \times \alpha(t)$$

### Safety Properties:
- **Clean Normal Preservation:** If $Z_t$ is small ($Z_t \approx 0.5$), $\alpha(t) \approx 0.20$, suppressing spurious historical reconstruction error below the threshold.
- **Active Anomaly Safety:** If an anomaly occurs during recovery ($Z_t > Z_{\text{bound}}$ or $\Delta S(t) > 0$), $\alpha(t) = 1.0$ and the detector instantly resets to `ACTIVE_ANOMALY`.

---

## 5. Leakage Prevention & Experimental Protocol

- **Dataset Partitions:** 70% Train, 15% Validation, 15% Test.
- **Calibration:** Decision thresholds tuned strictly on the 15% validation partition.
- **Causality:** Zero future telemetry or test labels accessed during state transitions.
