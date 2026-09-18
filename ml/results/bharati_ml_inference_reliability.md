# Bharati ML Inference Reliability & Edge-Case Hardening Report

## Executive Summary
- **Station**: Bharati (`BRT`)
- **Model Version**: `lstm-ae-bharati-v1`
- **Reconstruction Decision Threshold**: `0.013215307652775843`
- **Sliding History Window**: Exactly 30 observations per sensor channel
- **Validation Scope**: Edge cases, non-finite values, duplicate/stale timestamps, timezone normalization, missing data resets, sensor buffer isolation, and artifact integrity.
- **Overall Result**: **PASS (100% Reliability Coverage Across All 5 Bharati Sensors)**

---

## Hardened Reliability Scenarios

| Category | Input / Trigger Condition | Hardened Engine Behavior | Integrity Verification | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Timestamp Validation** | Valid ISO-8601 with mixed timezone offsets (`Z`, `+05:30`, `-04:00`, naive). | Normalized to UTC datetime semantics; equivalent moments across offsets detected as duplicates; malformed strings rejected with `InvalidContractError`. | Zero timezone comparison errors; UTC preservation. | `PASS` |
| **Duplicate Telemetry** | Identical timestamp received twice for the same sensor channel. | `DuplicateTelemetryError` raised immediately; buffer is not advanced and last processed timestamp remains unchanged. | Rolling buffer length unchanged; no duplicated tensors. | `PASS` |
| **Stale Telemetry** | Out-of-order timestamp older than previously recorded timestamp. | `StaleTelemetryError` raised immediately; older observation discarded without mutating buffer. | Chronological window order strictly preserved. | `PASS` |
| **Non-Finite Values** | Ingestion of `NaN`, `+inf`, `-inf`. | Detected before normalization; safely routed to `MISSING_DATA` (`score=null`, `type=null`); buffer cleared to prevent NaN tensor contamination. | Neural network receives zero NaN / Inf inputs. | `PASS` |
| **Quality & Dropout** | Ingestion of `value=None` or non-`GOOD` quality flags (`BAD`, `MISSING`, `UNCERTAIN`). | Output returned as `MISSING_DATA` (`score=null`, `type=null`); sensor history cleared; next valid observation starts fresh warmup (`INSUFFICIENT_DATA`). | Explicit buffer reset; prevents stale sequence continuation. | `PASS` |
| **Contract Hardening** | Ingestion of invalid station (`MTR`, `STATION_X`), invalid sensor (`TEMP_001`, `RADIATION_001`), or malformed payload. | Explicit typed errors raised (`UnsupportedStationError`, `UnsupportedSensorError`, `InvalidContractError`) without corrupting internal state. | Valid sensors remain ready immediately after rejection. | `PASS` |
| **Exact 30-Point Window** | Streaming continuous telemetry points (0 to 50 steps). | Steps 1–29 yield `INSUFFICIENT_DATA`; step 30 yields first scored inference; steps 31+ discard oldest point via `collections.deque(maxlen=30)` maintaining exactly 30 points. | Bounded memory consumption; deterministic rolling inference. | `PASS` |
| **State Isolation** | Interleaved concurrent streams across all 5 Bharati sensors. | Each sensor has an isolated history buffer; buffer reset on one sensor does not mutate or clear other sensors. | Zero cross-sensor contamination across all 5 channels. | `PASS` |
| **Determinism** | Repeated execution of identical telemetry sequences across separate service instances. | Bitwise identical anomaly scores, statuses, and classified types across independent runs. | Deterministic reproducibility with zero runtime variance. | `PASS` |
| **Artifact Integrity** | Service startup verification against cryptographic manifest (`lstm-ae-bharati-v1_manifest.json`). | Verified SHA-256 hashes and byte sizes for model weights, config, scalers, and threshold; corrupted files trigger `ModelIntegrityError`. | Production model and configuration verified on init. | `PASS` |

---

## 5 Bharati Sensor Channels Covered

1. `BRT_TEMP_001` (Ambient/Structural Temperature, °C)
2. `BRT_PRESS_001` (Atmospheric Pressure, hPa)
3. `BRT_HUM_001` (Relative Humidity, %)
4. `BRT_VIB_001` (Structural Vibration, mm/s)
5. `BRT_POWER_001` (Station Power Consumption, kW)

---

## Known Limitations & Synthetic Scope
- **Offline Synthetic Scope**: All reliability and edge-case validations were executed strictly on synthetic Antarctic telemetry engineered for Bharati station (`BRT`). No physical Antarctic hardware deployment is claimed.
