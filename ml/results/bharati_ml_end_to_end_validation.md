# Bharati ML End-to-End Pipeline Validation Report

## Executive Summary
- **Station**: Bharati (`BRT`)
- **Model Version**: `lstm-ae-bharati-v1`
- **Reconstruction Threshold**: `0.013215307652775843` (Frozen)
- **Supported Sensors**: `BRT_TEMP_001`, `BRT_PRESS_001`, `BRT_HUM_001`, `BRT_VIB_001`, `BRT_POWER_001`
- **Total Records Processed**: 1,093
- **Overall Pipeline Status**: **PASS (ALL SCENARIOS VALIDATED)**

---

## Validated Scenarios & Observed Behaviors

| Scenario # | Scenario Name | Description & Invariant | Expected Behavior | Observed Behavior | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Normal Telemetry** | Consecutive standard observations across all 5 Bharati sensors. | Observations 1–29 yield `INSUFFICIENT_DATA` (score=None, type=None); observation 30+ yields finite anomaly score; `NORMAL` status produces `NORMAL` type. | 29 initial warmup steps per sensor; all 30+ steps produced finite MSE score; `NORMAL` type strictly emitted. | `PASS` |
| **2** | **Spike Anomaly** | 30 normal warmup steps followed by abrupt high-magnitude shock jump. | Inference produces elevated reconstruction score > threshold (`0.013215`); anomaly status becomes `ANOMALY`; anomaly type is `SPIKE` or `UNKNOWN`. | Score exceeded threshold; status flagged `ANOMALY`; classifier identified `SPIKE` signature. | `PASS` |
| **3** | **Drift Anomaly** | 30 normal warmup steps followed by monotonic directional ramp. | Sustained linear deviation increases reconstruction error above threshold; type classifier assigns `DRIFT` or `UNKNOWN`. | Persistent slope detected; status flagged `ANOMALY`; classifier assigned `DRIFT`. | `PASS` |
| **4** | **Stuck Value** | 30 normal warmup steps followed by frozen telemetry flatline. | Pipeline maintains numeric stability; score and status evaluated deterministically; classifier detects flatline variance collapse. | Stability maintained; zero crashes; classifier assigned `STUCK_VALUE`. | `PASS` |
| **5** | **Dropout & Missing Data** | Ingestion of `value=None` or non-`GOOD` quality records. | Output status is `MISSING_DATA` (score=None, type=None); rolling window buffer cleared; subsequent point requires warm-up again. | Output is `MISSING_DATA`; history buffer reset; next valid observation emitted `INSUFFICIENT_DATA`. | `PASS` |
| **6** | **Insufficient Data** | Streaming fewer than 30 observations (< sequence length). | Output status is `INSUFFICIENT_DATA`; anomaly score and anomaly type remain `None`. | Strictly returned `INSUFFICIENT_DATA` with `score=None` and `type=None`. | `PASS` |
| **7** | **Multi-Sensor Isolation** | Interleaved concurrent telemetry streams across all 5 Bharati sensors. | Each sensor maintains strictly independent rolling history; buffer clearing on one sensor does not affect others. | Zero cross-sensor contamination; all 5 sensors inferenced independently. | `PASS` |
| **8** | **Duplicate Telemetry** | Telemetry with an identical timestamp arriving twice for the same sensor. | Duplicate rejected via `DuplicateTelemetryError`; buffer state remains uncorrupted. | Duplicate error raised immediately; subsequent valid telemetry processed normally. | `PASS` |
| **9** | **Stale Telemetry** | Telemetry with an out-of-order / older timestamp arriving. | Out-of-order record rejected via `StaleTelemetryError`; buffer state remains uncorrupted. | Stale error raised immediately; buffer state preserved. | `PASS` |
| **10** | **Contract & Input Hardening** | Ingestion of unsupported station (`MTR`), unsupported sensor (`TEMP_001`), empty strings, NaN, inf, or bad quality. | Strict contract validation raises typed exception or maps to `MISSING_DATA`. | All invalid and out-of-scope inputs safely rejected or sanitized. | `PASS` |
| **11** | **JSON Serialization** | Serialization and deserialization roundtrips of `BharatiTelemetryOutput`. | Bitwise / lossless roundtrip for all streaming states (`NORMAL`, `ANOMALY`, `INSUFFICIENT_DATA`, `MISSING_DATA`). | Full JSON serialization roundtrip verified with 100% field preservation. | `PASS` |
| **12** | **Artifact Integrity** | Cryptographic verification of model weights, config, scaler, and threshold on initialization. | `validate_model_artifacts` verifies all SHA-256 hashes and file sizes; corrupted artifacts trigger `ModelIntegrityError`. | Live artifacts validated (`VALID`); sandboxed corruptions strictly caught and rejected. | `PASS` |

---

## Status & Anomaly Type Distributions

### Output Status Counts (1,093 Total Observations)
- **`INSUFFICIENT_DATA`**: 693 records (warm-up phases)
- **`ANOMALY`**: 279 records (injected synthetic anomalies)
- **`NORMAL`**: 119 records (steady-state standard telemetry)
- **`MISSING_DATA`**: 2 records (null value and bad quality test records)

### Output Anomaly Type Counts
- **`NONE`** (Warmup / Missing): 695
- **`NORMAL`**: 119
- **`DRIFT`**: 108
- **`STUCK_VALUE`**: 65
- **`SPIKE`**: 60
- **`UNKNOWN`**: 46

---

## Known Limitations & Domain Boundary Notes
1. **Temporal Deviation vs. Constant Offset**: The LSTM Autoencoder evaluates reconstruction residuals over temporal patterns. An anomaly that holds a constant value within the nominal operating envelope may produce lower MSE than a high-frequency spike, relying on the rule-based anomaly classifier to detect the lack of physical variance.
2. **Synthetic Telemetry Scope**: All datasets, operating points, and validation runs are constructed on synthetic Antarctic telemetry engineered for Bharati station (`BRT`). No claim is made regarding deployment on real physical Antarctic station hardware.
