# Bharati ML Inference Observability & Structured Audit Layer

**Polarix Smart India Hackathon 2026 — Team Byte Me_26 (Team ID: 143760)**  
**Person C — ML Specialist Scope (Step 33)**  
**Station**: Bharati (`BRT`)  
**Frozen Model Version**: `lstm-ae-bharati-v1`  
**Frozen Reconstruction Threshold**: `0.013215307652775843`  
**Evaluation Scope**: **Synthetic / Test-Workload Diagnostics Only (Offline Validation)**

---

## 1. Executive Summary & Objective

Step 33 introduces a lightweight, deterministic, and framework-independent **Observability and Audit Layer** around the Bharati ML Inference Service (`BharatiMLService`). 

The observability layer captures structured, high-resolution diagnostic audit records for every processed telemetry observation without modifying model weights, scalers, thresholds, sequence buffer logic, or the frozen integration contracts. This enables full operational traceability, offline replay verification, root-cause diagnosis of rejected/malformed telemetry, sequence buffer evolution tracking, and aggregate performance monitoring across synthetic workloads.

> [!NOTE]
> **Synthetic Validation Disclaimer**: All metrics, latencies, and diagnostic logs reported herein are derived strictly from synthetic validation workloads and offline unit/integration test suites. No real Antarctic operational telemetry was used.

---

## 2. Structured Inference Audit Record (`BharatiInferenceAuditRecord`)

Every interaction with `BharatiMLService.process_telemetry()` emits a structured, immutable `BharatiInferenceAuditRecord`.

### Core Audit Fields

| Field | Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `str` (ISO-8601) | Normalized UTC observation timestamp. |
| `station_id` | `Optional[str]` | Target station identifier (`"BRT"`). |
| `sensor_id` | `Optional[str]` | Monitored Bharati sensor ID (`BRT_TEMP_001`, `BRT_PRESS_001`, `BRT_HUM_001`, `BRT_VIB_001`, `BRT_POWER_001`). |
| `input_value_present` | `bool` | Whether a valid numerical float value was supplied. |
| `input_quality` | `Optional[str]` | Input quality flag (`"GOOD"`, `"MISSING"`, `"SUSPECT"`, etc.). |
| `input_accepted` | `bool` | Boolean flag indicating whether telemetry passed contract validation. |
| `event_type` | `str` | Structured event classification (see Event Vocabulary below). |
| `anomaly_status` | `Optional[str]` | Resulting inference decision (`"NORMAL"`, `"ANOMALY"`, `"INSUFFICIENT_DATA"`, `"MISSING_DATA"`). |
| `anomaly_type` | `Optional[str]` | Classified anomaly type (`"NORMAL"`, `"SPIKE"`, `"DRIFT"`, `"STUCK_VALUE"`, `"UNKNOWN"`). |
| `anomaly_score` | `Optional[float]` | Mean squared error (MSE) reconstruction loss produced by the LSTM Autoencoder. |
| `threshold` | `Optional[float]` | Frozen reconstruction threshold (`0.013215307652775843`). |
| `model_version` | `Optional[str]` | Frozen model version identifier (`"lstm-ae-bharati-v1"`). |
| `history_size_before` | `int` | Sliding window observation count before processing. |
| `history_size_after` | `int` | Sliding window observation count after processing. |
| `inference_eligible` | `bool` | Indicates whether window reached the required 30 observations for scored inference. |
| `state_changed` | `bool` | Indicates whether internal rolling state or timestamp was modified. |
| `processing_time_ms` | `float` | Monotonic processing latency measured in milliseconds. |
| `error_code` | `Optional[str]` | Structured error or exception class name if rejected. |
| `rejection_reason` | `Optional[str]` | Human-readable explanation for telemetry rejection or error. |

---

## 3. Deterministic Event Vocabulary

The observability layer categorizes every processed event using a deterministic, closed vocabulary:

| Event Type | Trigger Condition | Status / Outcome |
| :--- | :--- | :--- |
| `INFERENCE` | Valid observation with 30-observation sliding window completed. | `NORMAL` or `ANOMALY` with score and anomaly type. |
| `INSUFFICIENT_DATA` | Valid observation during buffer warmup phase ($< 30$ observations). | Buffer increments, `anomaly_status = INSUFFICIENT_DATA`. |
| `MISSING_DATA` | Telemetry with `value=None`, non-GOOD quality, or NaN/Inf floats. | Buffer resets to 0, `anomaly_status = MISSING_DATA`. |
| `DUPLICATE` | Identical timestamp for identical sensor submitted repeatedly. | `DuplicateTelemetryError` raised, state unchanged. |
| `STALE` | Out-of-order timestamp older than previously recorded timestamp. | `StaleTelemetryError` raised, state unchanged. |
| `INVALID_INPUT` | Malformed payload, invalid schema, unsupported station, or unknown sensor. | Contract exception raised, state unchanged. |
| `ERROR` | Unhandled or unexpected internal runtime exception. | Exception logged with diagnostic context. |

---

## 4. Latency Measurement & State Visibility

### Monotonic Timing
- Execution durations are measured strictly using `time.perf_counter()` to ensure high-resolution monotonicity unaffected by system clock adjustments or NTP syncs.
- Durations are recorded in milliseconds (`processing_time_ms`), rounded to 4 decimal places, and guaranteed to be non-negative and finite.

### Rolling Window State Tracking
- State evolution is captured via `history_size_before` and `history_size_after` without exposing or duplicating entire raw observation arrays.
- Sensor isolation is strictly preserved: buffer state for each sensor (`BRT_TEMP_001` through `BRT_POWER_001`) operates independently.

---

## 5. Model Traceability & Cryptographic Integrity

Every audit record generated during scored inference or buffer operations identifies:
- `model_version`: `lstm-ae-bharati-v1`
- `threshold`: `0.013215307652775843`

Artifact integrity is cryptographically validated at startup via SHA-256 hashes:
- `lstm-ae-bharati-v1.pt`: `412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a`
- `lstm-ae-bharati-v1_config.json`: `16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7`
- `lstm-ae-bharati-v1_scaler.json`: `b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899`
- `bharati_lstm_threshold.json`: `95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d`

---

## 6. Serialization & Aggregate Diagnostics

### RFC 8259 JSON Serialization
- Full support for `.to_dict()`, `.to_json()`, `.from_dict()`, and `.from_json()`.
- Guaranteed sanitization of `NaN`, `Infinity`, and `-Infinity` into `None` / `null`.

### Aggregation Utility (`summarize_audit_records`)
Provides summary metrics across collections of audit records:
- Total events, accepted events, and rejected event counts.
- Event breakdown across all 7 supported event types.
- Anomaly status and anomaly type frequency distributions.
- Latency percentiles: Average, P50, P95, Min, and Max execution time in ms.

---

## 7. Validation Test Results

The observability suite was verified against comprehensive unit and integration tests:

| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_1_audit_record_valid` | Schema validation & field integrity | **PASS** |
| `test_2_audit_record_invalid_event_type` | Rejection of unsupported event types | **PASS** |
| `test_3_audit_record_invalid_timing` | Rejection of non-finite or negative latency | **PASS** |
| `test_4_insufficient_data_audit` | Warmup buffer evolution & status tracking | **PASS** |
| `test_5_successful_normal_inference_audit` | Normal inference audit & score propagation | **PASS** |
| `test_6_successful_anomaly_inference_audit` | Anomaly inference audit & type classification | **PASS** |
| `test_7_missing_data_audit` | Missing telemetry audit & buffer reset | **PASS** |
| `test_8_nan_value_missing_data_audit` | NaN input safety & buffer reset | **PASS** |
| `test_9_duplicate_rejection_audit` | Duplicate timestamp rejection logging | **PASS** |
| `test_10_stale_rejection_audit` | Out-of-order timestamp rejection logging | **PASS** |
| `test_11_invalid_station_and_sensor_audit` | Invalid station/sensor diagnostic logging | **PASS** |
| `test_12_model_version_and_threshold_traceability` | Model version and threshold verification | **PASS** |
| `test_13_sensor_state_isolation` | Independent multi-sensor buffer tracking | **PASS** |
| `test_14_json_roundtrip_serialization` | RFC 8259 JSON serialization roundtrip | **PASS** |
| `test_15_aggregate_diagnostics_summary` | Summary counts and latency statistics | **PASS** |
| `test_16_deterministic_repeated_sequence` | Replay determinism across fresh instances | **PASS** |

**Summary**: 16/16 tests passed (100% pass rate).

---

## 8. Known Limitations & Operational Scope

1. **In-Memory Bounded History**: By default, `BharatiMLService` retains up to 100 recent audit records in an in-memory deque to prevent memory leaks in long-running processes. Downstream orchestrators requiring permanent audit persistence should stream records to an external logging/database sink.
2. **Synthetic Workload Profiling**: Latency metrics reflect local CPU execution time on synthetic telemetry streams and should be re-benchmarked in target production hardware environments.
3. **Stateless Service Restart**: Rolling sequence buffers and diagnostic records are in-memory; service restarts require warm-up (30 points) unless externally restored.
