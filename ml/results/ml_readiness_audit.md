# Polarix ML Final Readiness Audit

**Project:** Polarix — Smart India Hackathon 2026  
**Problem Statement:** SIH26060  
**Team:** Byte Me_26 (Team ID: 143760)  
**Role:** Person C (Machine Learning Specialist)  
**Branch:** `Rex`  
**Status:** `ML SUBSYSTEM — READY FOR INTEGRATION`  
**Timestamp:** 2026-09-18T12:00:00Z  

---

## 1. Audit Scope

This document constitutes the official, reproducible integration sign-off audit for the Polarix Machine Learning subsystem (Steps 1–37). It covers complete verification of both Antarctic research stations: **Maitri (`MTR`)** and **Bharati (`BRT`)**.

The Polarix ML pipeline is hybrid: LSTM reconstruction scoring provides anomaly detection/scoring, deterministic downstream classification identifies anomaly types where supported, and explicit missing-data handling covers dropout/offline telemetry.

---

## 2. Repository Integrity

All ML components adhere to a clean, modular repository layout without extraneous artifacts or broken links:
- `ml/data/`: Deterministic synthetic dataset generators and schemas.
- `ml/models/`: Frozen PyTorch LSTM autoencoder weights, fitted scalers, and architectures.
- `ml/inference/`: Production inference services, input/output contract adapters, deterministic classifiers, and observability loggers.
- `ml/results/`: Evaluation reports, calibration analyses, latency benchmark profiles, and signed handoff contracts.
- `ml/tests/`: 440+ automated pytest unit, integration, reliability, and regression tests.

---

## 3. Maitri Readiness

| Property | Specification | Validation Status |
| :--- | :--- | :--- |
| Station ID | `MTR` | Verified |
| Model Version | `lstm-ae-v1` | Verified |
| Decision Threshold | `0.017674` | Verified |
| Sequence Length | 30 observations | Verified |
| Supported Sensors | `TEMP_001`, `PRESS_001`, `HUM_001`, `VIB_001`, `POWER_001` | Verified (5/5) |
| Completed Steps | Steps 1–22 — Maitri Complete | Verified |

---

## 4. Bharati Readiness

| Property | Specification | Validation Status |
| :--- | :--- | :--- |
| Station ID | `BRT` | Verified |
| Model Version | `lstm-ae-bharati-v1` | Verified |
| Decision Threshold | `0.013215307652775843` | Verified (Exact) |
| Sequence Length | 30 observations | Verified |
| Supported Sensors | `BRT_TEMP_001`, `BRT_PRESS_001`, `BRT_HUM_001`, `BRT_VIB_001`, `BRT_POWER_001` | Verified (5/5) |
| Completed Steps | Steps 23–36 — Bharati ML + Handoff Complete | Verified |
| Refinements & Audits | Steps 38–42 (Refinements, Re-Evaluation & Final Readiness) | Verified |

---

## 5. Frozen Artifact Integrity

All 8 frozen ML artifacts — 2 models, 2 configs, 2 scalers, and 2 decision thresholds — match their expected SHA-256 digests:

| Artifact Path | Expected SHA-256 Digest | Audit Status |
| :--- | :--- | :---: |
| `ml/models/lstm-ae-bharati-v1.pt` | `412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a` | **PASSED** |
| `ml/models/lstm-ae-bharati-v1_config.json` | `16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7` | **PASSED** |
| `ml/models/lstm-ae-bharati-v1_scaler.json` | `b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899` | **PASSED** |
| `ml/results/bharati_lstm_threshold.json` | `95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d` | **PASSED** |
| `ml/models/lstm-ae-v1.pt` | `7ff138f30ef85b7d4fcd5c558e7394257f492254a295053b267e2dc07f3f1262` | **PASSED** |
| `ml/models/lstm-ae-v1_config.json` | `71c61e98c364d34ed37505fd97d6e96757904ab016768fcdc8058e0fa8ca720b` | **PASSED** |
| `ml/models/lstm-ae-v1_scaler.json` | `2371bec3fbcb8664e4f7ab832ffc5a659b1057d1cf8401eeb368134682c60224` | **PASSED** |
| `ml/results/lstm_threshold.json` | `80c7c2af48a2b7a9d49e7e10c98859b6d2c368c732fb4f273431697e917707c1` | **PASSED** |

---

## 6. Model/Version Contract

- **Maitri**: Model version strictly mapped to `lstm-ae-v1`.
- **Bharati**: Model version strictly mapped to `lstm-ae-bharati-v1`.
- **Isolation**: Independent sliding window buffers per sensor (30-point rolling window).
- **State Reset**: `MISSING_DATA` or non-GOOD quality telemetry flushes sensor buffer to length 0.

---

## 7. Input/Output Contract

- **Canonical Input Fields**: `station_id`, `sensor_id`, `timestamp` (ISO-8601 UTC), `value` (numeric), `unit`, `quality`, `source`.
- **Canonical Output Fields**: `station_id`, `sensor_id`, `timestamp`, `value`, `unit`, `quality`, `source`, `anomaly_score`, `anomaly_status`, `anomaly_type`, `model_version`.
- **Statuses Supported**: `NORMAL`, `ANOMALY`, `INSUFFICIENT_DATA`, `MISSING_DATA`.
- **Anomaly Types Supported**: `NORMAL`, `SPIKE`, `DRIFT`, `STUCK_VALUE`, `UNKNOWN`.
- **Nullable Rules**: `anomaly_score` and `anomaly_type` are strictly `null` during `INSUFFICIENT_DATA` and `MISSING_DATA`.

---

## 8. Scenario Coverage

Both stations have undergone comprehensive scenario evaluations across representative telemetry patterns:
- `NORMAL_DAY`: Stable diurnal cycles with nominal reconstruction loss.
- `SPIKE`: Instantaneous amplitude transient detection and physical classification.
- `DRIFT`: Sustained directional trend divergence detection.
- `STUCK_VALUE`: Flatline sensor condition detection via downstream deterministic classifier.
- `MISSING_DATA` / `DROPOUT`: Buffer flush and `MISSING_DATA` emission via structured quality handling.
- `INSUFFICIENT_DATA`: Deterministic warmup bypass for sequences < 30 observations.
- `DUPLICATE_TELEMETRY` & `STALE_TELEMETRY`: Diagnostic rejection error tracking.
- `MULTI_SENSOR_ISOLATION`: Zero cross-talk across interleaved telemetry streams.

---

## 9. Authoritative Model Evaluation Metrics

### Bharati Baseline & LSTM Tradeoffs:

| Evaluation Slice | Model / Detector | Precision | Recall | F1 Score | False Positive Rate | Accuracy |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Bharati Test Set** | Z-Score (3.0σ Baseline) | 0.7167 | 0.1356 | 0.2281 | 1.44% | 80.60% |
| **Bharati Test Set** | LSTM Autoencoder (`lstm-ae-bharati-v1`) | 0.2679 | 0.5709 | 0.3646 | 50.50% | 51.36% |
| **Bharati Validation Set** | LSTM Autoencoder (`lstm-ae-bharati-v1`) | 0.2949 | 0.6301 | 0.4017 | 49.49% | 52.48% |

> [!NOTE]
> Tradeoff Summary: The Z-Score baseline provides low false-positive rates on static limits but fails on temporal anomalies (low recall 13.56%). The LSTM autoencoder captures subtle dynamic pattern anomalies (higher recall 57.09%) at the cost of higher synthetic false-positive rate (50.50%).

---

## 10. Documentation & Handoff Evidence

- **Handoff Guide**: [`ml/ML_HANDOFF.md`](file:///Users/rexjohnabraham/Documents/Polarix_C/ml/ML_HANDOFF.md) — 17 complete technical sections covering integration checklists, schemas, and flow examples.
- **Machine-Readable Contract**: [`ml/results/ml_handoff_contract.json`](file:///Users/rexjohnabraham/Documents/Polarix_C/ml/results/ml_handoff_contract.json) — Structured schema definitions and artifact registries.
- **Ownership Boundaries**: Person C (ML Specialist), Person A (Backend), and Person B (Frontend) responsibilities strictly delineated without overlap.

---

## 11. Known Limitations & Scope Boundaries

1. **Synthetic Telemetry Only**: Evaluated and benchmarked entirely on synthetic telemetry datasets.
2. **No Real Antarctic Historical Data**: Field historical operational data was not accessible for training.
3. **In-Memory Rolling State**: Sliding window buffers reside in memory and reset upon service restart.
4. **Reconstruction False-Positive Rate**: Bharati LSTM test FPR is 50.50% on diurnal variations to maximize anomaly recall.
5. **STUCK_VALUE / Flatline Reconstruction Limitation**: STUCK_VALUE/flatline conditions may not always produce sufficiently high LSTM reconstruction error; the downstream deterministic classifier identifies some STUCK_VALUE patterns independently of the LSTM anomaly decision.
6. **Hybrid Pipeline Scope**: The LSTM model itself does not detect all SPIKE, DRIFT, STUCK_VALUE, and DROPOUT cases alone; no claim of perfect anomaly-type classification is made.
7. **Anomaly Score Interpretation**: MSE reconstruction loss is an anomaly severity index, not a calibrated Bayesian probability.
8. **Prototype Scope**: Designed for SIH 2026 integration demonstration; not certified for physical Antarctic mission deployment.

---

## 12. Integration Readiness

The Machine Learning subsystem is confirmed ready for seamless integration with Person A (FastAPI Backend) and Person B (React/Three.js Frontend).

---

## 13. Final Sign-Off

**Official Verdict:** `ML SUBSYSTEM — READY FOR INTEGRATION`  
**Sign-off Statement:** The Polarix Machine Learning subsystem across Maitri and Bharati is fully verified, cryptographically frozen, and ready for consumption by Person A (Backend) and Person B (Frontend).
