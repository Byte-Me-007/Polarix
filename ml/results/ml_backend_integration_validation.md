# Polarix ML ↔ Backend Integration Contract Validation Report

**Smart India Hackathon 2026 — Team Byte Me_26 (Team ID: 143760)**  
**Role:** Person C — Machine Learning Specialist (Step 43)  
**Validation Timestamp:** 2026-09-18T07:13:02.578080+00:00  
**Overall Status:** `INTEGRATION_CONTRACT_VALIDATED` (10/10 Checks PASS)  

---

## 1. Executive Summary & Integration Boundary Scope

> [!NOTE]
> **Synthetic Telemetry Disclaimer**: All integration validations and payload evaluations are conducted strictly using synthetic telemetry payloads formatted to match the Polarix backend contract. No real Antarctic station operational telemetry was used.

This report validates the exact integration boundary between Person A's backend (FastAPI / MQTT) and Person C's ML services (`MaitriMLService`, `BharatiMLService`). It exercises payload ingestion, error boundaries, state management, scenario classification, and response serialization.

---

## 2. Integration Boundary Categorization

### A. Validated Directly (ML-Side Integration Boundary)
- [x] Backend-style dictionary and JSON string payload ingestion (adapt_backend_input).
- [x] Canonical 11-field response serialization and JSON roundtrip (adapt_backend_output).
- [x] Cold-start warmup (< 30 observations) routing to INSUFFICIENT_DATA with null scores.
- [x] Normal stationary telemetry scored inference against frozen threshold.
- [x] SPIKE anomaly detection and physical classification.
- [x] DRIFT monotonic trend detection and trajectory classification.
- [x] STUCK_VALUE active flatline detection and zero-false-alarm recovery behavior.
- [x] MISSING_DATA ingestion on null, NaN, Inf, or bad-quality telemetry with immediate buffer flush.
- [x] DuplicateTelemetryError and StaleTelemetryError rejection boundaries.
- [x] Multi-sensor rolling buffer isolation across all 10 station channels (5 MTR, 5 BRT).

### B. Validated Through Backend Code
- No backend server execution claimed on Person C branch: Person A's FastAPI, MQTT broker, and SQLite persistence are isolated on Person A branches and validated via standardized contracts.

### C. Not Yet Validated (Person A Backend Scope)
- [ ] Live MQTT broker subscription and network transport latency.
- [ ] FastAPI REST / WebSocket route dispatch and real-time client fanout.
- [ ] SQLite relational schema migration and database write throughput.
- [ ] Operational multi-step escalation business rules (e.g. 3-step alarm hysteresis).

---

## 3. Integration Check Matrix

| # | Integration Check Category | Description | Latency | Result |
| :---: | :--- | :--- | :---: | :---: |
| 1 | `Input Contract Parsing` | Validation of dictionary and JSON string payl... | `0.0348 ms` | **PASS** |
| 2 | `Streaming Warmup` | Verification of INSUFFICIENT_DATA status and ... | `0.8134 ms` | **PASS** |
| 3 | `Normal Scored Inference` | Validation that 30-step nominal stationary te... | `13.6256 ms` | **PASS** |
| 4 | `SPIKE Anomaly` | Validation that sudden high-amplitude step ju... | `1.5505 ms` | **PASS** |
| 5 | `DRIFT Anomaly` | Validation that sustained monotonic linear ra... | `1.4937 ms` | **PASS** |
| 6 | `STUCK_VALUE & Recovery` | Validation that active flatlines trigger STUC... | `42.0115 ms` | **PASS** |
| 7 | `MISSING_DATA Ingestion` | Validation that null, NaN, and non-GOOD telem... | `0.0313 ms` | **PASS** |
| 8 | `Duplicate & Stale Rejection` | Validation that duplicate timestamps raise Du... | `0.1968 ms` | **PASS** |
| 9 | `Multi-Sensor Isolation` | Validation of independent buffer isolation ac... | `1.1357 ms` | **PASS** |
| 10 | `Output Contract & JSON Roundtrip` | Validation that all 11 canonical contract fie... | `0.4644 ms` | **PASS** |

---

## 4. Canonical Contract Vocabulary & Semantics

### Status Vocabulary (`anomaly_status`):
- `NORMAL`: Sequence reconstruction MSE $\le$ threshold. Scored forward pass executed.
- `ANOMALY`: Sequence reconstruction MSE $>$ threshold. Scored forward pass executed.
- `INSUFFICIENT_DATA`: Sequence buffer $< 30$ observations. Model forward pass bypassed; score and type are `null`.
- `MISSING_DATA`: Non-GOOD quality, null, or non-finite telemetry. Buffer immediately cleared to 0; score and type are `null`.

### Anomaly Type Vocabulary (`anomaly_type`):
- `NORMAL`: Baseline non-anomalous telemetry.
- `SPIKE`: Instantaneous high-amplitude step jump exceeding local variance.
- `DRIFT`: Sustained monotonic directional trend across window.
- `STUCK_VALUE`: Active sensor flatline condition (isolated at tail, 0 recovery false alarms).
- `UNKNOWN`: Anomaly detected by LSTM autoencoder without a single archetype heuristic match.

---

## 5. Multi-Sensor Stream Isolation

Independent 30-step sliding window buffers (`collections.deque(maxlen=30)`) are strictly maintained per `(station_id, sensor_id)` pair across all 10 supported channels:
- **Maitri (`MTR`)**: `TEMP_001`, `PRESS_001`, `HUM_001`, `VIB_001`, `POWER_001`
- **Bharati (`BRT`)**: `BRT_TEMP_001`, `BRT_PRESS_001`, `BRT_HUM_001`, `BRT_VIB_001`, `BRT_POWER_001`

A missing-data event or error on one sensor channel resets only that channel's rolling buffer without impacting adjacent streams.

---

## 6. Final Integration Readiness Conclusion

The ML subsystem boundary is **fully validated, robustly guarded against edge cases, and ready for end-to-end orchestration** by Person A (Backend) and Person B (Frontend).
