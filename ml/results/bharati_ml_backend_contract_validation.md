# Bharati ML Backend Integration Contract Validation Report

## Executive Summary
- **Module**: `ml.inference.bharati_backend_contract`
- **Station**: Bharati (`BRT`)
- **Model Version**: `lstm-ae-bharati-v1`
- **Reconstruction Threshold**: `0.013215307652775843`
- **Scope**: Validation of Person C's ML service boundary and conversion adapters for Person A's backend consumption.
- **Status**: **PASS (ALL 12 CASES VERIFIED)**

---

## Standard Integration Architecture

```text
Person A Backend
      ↓
Backend JSON Dictionary / String
      ↓
adapt_backend_input() → BharatiTelemetryInput (Contract Validation)
      ↓
BharatiMLService.process_telemetry()
      ↓
BharatiTelemetryOutput
      ↓
adapt_backend_output() → Backend Response Dictionary (Strict JSON Compliant)
      ↓
Person A Backend / REST / WebSocket / MQTT
```

---

## Contract Schemas

### 1. Ingestion Input Schema (`BharatiTelemetryInput`)

| Field Name | Type | Required | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `station_id` | `str` | Yes | Must strictly be `"BRT"`. | `"BRT"` |
| `sensor_id` | `str` | Yes | One of 5 supported Bharati sensors. | `"BRT_TEMP_001"` |
| `timestamp` | `str` | Yes | ISO-8601 UTC timestamp string. | `"2026-09-18T10:30:00Z"` |
| `value` | `float` or `None` | No | Numeric telemetry observation (or `null`). | `-10.5` |
| `unit` | `str` or `None` | No | Physical unit of measurement. | `"C"` |
| `quality` | `str` | No (default `"GOOD"`) | Telemetry quality flag (`"GOOD"`, `"BAD"`, `"MISSING"`, `"UNCERTAIN"`). | `"GOOD"` |
| `source` | `str` or `None` | No (default `"SIMULATOR"`) | Telemetry origin identifier. | `"SIMULATOR"` |

### 2. Standardized Backend Output Schema (`BharatiTelemetryOutput`)

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `station_id` | `str` | Echoed station identifier (`"BRT"`). |
| `sensor_id` | `str` | Echoed sensor identifier. |
| `timestamp` | `str` | Echoed ISO-8601 timestamp. |
| `value` | `float` or `None` | Sanitized numeric telemetry value (`null` if non-finite/missing). |
| `unit` | `str` or `None` | Physical unit of measurement. |
| `quality` | `str` | Telemetry quality flag. |
| `source` | `str` or `None` | Telemetry origin identifier. |
| `anomaly_score` | `float` or `None` | Raw LSTM reconstruction error (MSE). `null` during warmup/dropout. |
| `anomaly_status` | `str` | Streaming status: `"NORMAL"`, `"ANOMALY"`, `"INSUFFICIENT_DATA"`, `"MISSING_DATA"`. |
| `anomaly_type` | `str` or `None` | Classified signature: `"NORMAL"`, `"SPIKE"`, `"DRIFT"`, `"STUCK_VALUE"`, `"UNKNOWN"`. |
| `model_version` | `str` | Frozen model version (`"lstm-ae-bharati-v1"`). |

---

## Supported Domain Vocabularies

- **Supported Sensors**:
  1. `BRT_TEMP_001` (Ambient/Structural Temperature, °C)
  2. `BRT_PRESS_001` (Atmospheric Pressure, hPa)
  3. `BRT_HUM_001` (Relative Humidity, %)
  4. `BRT_VIB_001` (Structural Vibration, mm/s)
  5. `BRT_POWER_001` (Station Power Consumption, kW)
- **Supported Statuses**: `"NORMAL"`, `"ANOMALY"`, `"INSUFFICIENT_DATA"`, `"MISSING_DATA"`
- **Supported Anomaly Types**: `"NORMAL"`, `"SPIKE"`, `"DRIFT"`, `"STUCK_VALUE"`, `"UNKNOWN"`

---

## Scenario Verification Summary

| Case # | Test Case Description | Expected Result | Observed Status |
| :--- | :--- | :--- | :--- |
| **1** | Valid Normal Telemetry | Full 30-step warm-up produces `NORMAL` status and `NORMAL` anomaly type with finite score. | `PASSED` |
| **2** | Valid Anomaly Telemetry | Pulse shock produces `ANOMALY` status and `SPIKE` anomaly type with score > threshold. | `PASSED` |
| **3** | Insufficient History | Steps 1..29 produce `INSUFFICIENT_DATA` with `score=null` and `type=null`. | `PASSED` |
| **4** | Missing Telemetry | `value=null` produces `MISSING_DATA` and resets rolling history. | `PASSED` |
| **5** | Bad Quality Telemetry | `quality="BAD"` produces `MISSING_DATA` and resets rolling history. | `PASSED` |
| **6** | Non-Finite Values (NaN/Inf) | Replaced cleanly with `null` in JSON output, producing `MISSING_DATA`. | `PASSED` |
| **7** | Duplicate Timestamp | `DuplicateTelemetryError` raised without corrupting rolling buffer. | `PASSED` |
| **8** | Stale Telemetry | `StaleTelemetryError` raised on out-of-order timestamp without corrupting buffer. | `PASSED` |
| **9** | Unsupported Station | `UnsupportedStationError` raised when `station_id != "BRT"`. | `PASSED` |
| **10** | Unsupported Sensor | `UnsupportedSensorError` raised when `sensor_id` is unknown. | `PASSED` |
| **11** | Malformed Payload | `InvalidContractError` raised on malformed timestamps or invalid types. | `PASSED` |
| **12** | JSON Serialization Roundtrip | 100% metadata preservation and lossless JSON roundtrip verified. | `PASSED` |

---

## Error Boundaries & Contract Isolation
- **Backend Isolation**: Person A's backend never interacts with PyTorch models, weight tensors, or scalers. It communicates strictly via dictionaries or JSON strings.
- **Expected Rejection vs Service Error**: Rejections (duplicates, stale timestamps, invalid stations/sensors) raise explicit domain exceptions (`InvalidContractError`, `DuplicateTelemetryError`, `StaleTelemetryError`, `UnsupportedSensorError`, `UnsupportedStationError`) rather than returning a silent false `NORMAL` status.

---

## Synthetic Data Disclaimer
*All tests and schema validations are performed strictly in an offline synthetic environment using synthetic telemetry engineered for Bharati station (`BRT`). No claims are made regarding real Antarctic hardware deployments.*
