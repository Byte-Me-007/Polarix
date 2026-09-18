# Bharati ML Model Versioning & Artifact Integrity Report

## Executive Summary
- **Station**: Bharati (`BRT`)
- **Model Version**: `lstm-ae-bharati-v1`
- **Model Type**: LSTM Autoencoder (`LSTMAutoencoder`)
- **Status**: **VALIDATED / PRODUCTION-READY**
- **Validation Status**: **PASS (ALL 4 ARTIFACTS VALID)**

---

## Frozen Artifact Register & SHA-256 Integrity Verification

| Role | File Path | Size (Bytes) | Cryptographic SHA-256 Hash | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Model Weights** | `ml/models/lstm-ae-bharati-v1.pt` | 50,757 | `412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a` | `VALID` |
| **Model Config** | `ml/models/lstm-ae-bharati-v1_config.json` | 218 | `16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7` | `VALID` |
| **Fitted Scalers** | `ml/models/lstm-ae-bharati-v1_scaler.json` | 691 | `b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899` | `VALID` |
| **Validation Threshold** | `ml/results/bharati_lstm_threshold.json` | 853 | `95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d` | `VALID` |

---

## Operational Hyperparameters & Model Specification

- **Sequence Window Length**: 30 observations (sliding window)
- **Input Feature Size**: 1 (univariate per sensor channel)
- **Hidden Dimensions**: 32 (LSTM encoder/decoder)
- **Latent Bottleneck**: 16
- **Number of Layers**: 1
- **Dropout**: 0.0
- **Loss Function**: Mean Squared Error (`MSELoss`)
- **Selected Decision Threshold**: `0.013215307652775843`
- **Supported Bharati Sensors**:
  1. `BRT_TEMP_001` (Ambient/Structural Temperature, °C)
  2. `BRT_PRESS_001` (Atmospheric Pressure, hPa)
  3. `BRT_HUM_001` (Relative Humidity, %)
  4. `BRT_VIB_001` (Structural Vibration, mm/s)
  5. `BRT_POWER_001` (Station Power Consumption, kW)

---

## Dataset Provenance & Synthetic Disclaimer

- **Training Dataset**: `ml/data/bharati_synthetic_telemetry.csv`
- **Version**: `10k_synthetic_v1`
- **Total Records**: 10,000 synthetic observations across 5 sensors
- **Data Splits**:
  - Training: 70% Normal-only (7,000 records / 6,855 sequences)
  - Validation: 15% mixed (1,500 records / 1,181 sequences)
  - Testing: 15% mixed (1,500 records / 1,182 sequences)
- **Random Seed**: `42` (strictly reproducible)
- **Disclaimer**: *All training and validation were conducted strictly on synthetic telemetry engineered for Bharati station. No real Antarctic telemetry was used.*

---

## Integrity Validation Lifecycle

```text
Service Initialization
        ↓
Load Manifest (ml/models/lstm-ae-bharati-v1_manifest.json)
        ↓
Cryptographic Verification (SHA-256 Checksum & File Size matching)
        ↓
Load Model Weights, Config, Scaler, & Threshold
        ↓
BharatiMLService Ready (Zero per-point validation overhead)
        ↓
Streaming Real-Time Telemetry Inference
```
