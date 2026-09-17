# Polarix Bharati LSTM Inference Service Validation Report (SIH26060 - Person C)

**Station:** Bharati (`BRT`)  
**Service Class:** `BharatiMLService` (`ml.inference.bharati_ml_service.BharatiMLService`)  
**Engine Class:** `BharatiLSTMInference` (`ml.inference.bharati_lstm_inference.BharatiLSTMInference`)  
**Model Version:** `lstm-ae-bharati-v1`  
**Frozen Decision Threshold:** `0.013215307652775843`  
**Required Window Length:** `30` observations  
**Status:** VALIDATED & READY FOR BACKEND CONSUMPTION  

---

> [!IMPORTANT]
> **SYNTHETIC DATA DISCLAIMER**:
> All inference validations and test vectors are executed strictly against synthetic Bharati telemetry schemas.
> No real Antarctic station sensor telemetry was used or claimed.

---

## 1. Supported Bharati Sensor Channels

| Sensor Identifier | Physical Quantity | Unit | Fitted Scaler Parameters |
| :--- | :--- | :--- | :--- |
| **`BRT_TEMP_001`** | Temperature | `°C` | $\mu = -12.0294$, $\sigma = 6.7906$ |
| **`BRT_PRESS_001`**| Atmospheric Pressure | `hPa` | $\mu = 984.7745$, $\sigma = 11.9610$ |
| **`BRT_HUM_001`**  | Relative Humidity | `%` | $\mu = 70.1584$, $\sigma = 10.7410$ |
| **`BRT_VIB_001`**  | Vibration Velocity | `mm/s` | $\mu = 1.4988$, $\sigma = 0.2882$ |
| **`BRT_POWER_001`**| Power Consumption | `kW` | $\mu = 47.8860$, $\sigma = 8.2673$ |

---

## 2. Streaming State Machine & Inference Protocol

```text
Incoming Telemetry Observation
           ↓
[1. Strict Schema & Contract Validation]
  ├── Non-finite / null / BAD quality ──────→ Reset sensor buffer ──→ Status: MISSING_DATA (score: null)
  ├── Out-of-order timestamp (stale) ───────→ Reject (StaleTelemetryError)
  ├── Duplicate timestamp ──────────────────→ Reject (DuplicateTelemetryError)
  └── Valid finite reading
           ↓
[2. Sensor Buffer Ingestion]
  ├── Buffered points < 30 ─────────────────→ Status: INSUFFICIENT_DATA (score: null)
  └── Buffered points == 30
           ↓
[3. PyTorch LSTM Autoencoder Forward Pass]
  ├── Reconstruct normalized 30-step sequence
  └── Compute Mean Squared Error (MSE)
           ↓
[4. Frozen Threshold Comparison (0.013215)]
  ├── MSE <= 0.013215 ──────────────────────→ Status: NORMAL (score: MSE)
  └── MSE >  0.013215 ──────────────────────→ Status: ANOMALY (score: MSE)
```

---

## 3. Sample Case Validations

- **Insufficient Data Case:** Correctly emits `anomaly_status = "INSUFFICIENT_DATA"` with `anomaly_score = null` when $< 30$ observations are buffered.
- **Normal Inference Case:** When fed with 30 steady in-distribution readings, outputs `anomaly_status = "NORMAL"` with finite MSE score $\le 0.013215$.
- **Anomaly Inference Case:** When fed with an out-of-distribution spike excursion, outputs `anomaly_status = "ANOMALY"` with MSE score $> 0.013215$.
- **Missing Data & Recovery Case:** Non-finite values or `quality != "GOOD"` emit `anomaly_status = "MISSING_DATA"` with `anomaly_score = null` and clear the buffer to prevent corruption of subsequent rolling sequences.
- **Contract Enforcement:** Unsupported stations (`UnsupportedStationError`), unsupported sensors (`UnsupportedSensorError`), duplicate timestamps (`DuplicateTelemetryError`), and stale timestamps (`StaleTelemetryError`) are deterministically rejected.

---

## 4. Service Artifact Dependencies

- **Model Weights:** `ml/models/lstm-ae-bharati-v1.pt`
- **Model Config:** `ml/models/lstm-ae-bharati-v1_config.json`
- **Fitted Scalers:** `ml/models/lstm-ae-bharati-v1_scaler.json`
- **Frozen Threshold:** `ml/results/bharati_lstm_threshold.json`
