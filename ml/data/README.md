# Polarix ML — Maitri Synthetic Telemetry Dataset

## Overview & Synthetic Data Notice
This dataset contains purely **synthetic** multi-sensor telemetry engineered for developing, benchmarking, and validating machine learning anomaly detection pipelines for the **Maitri Antarctic Station (`MTR`)** under Smart India Hackathon 2026 (SIH26060).

> **IMPORTANT DISCLAIMER:** This dataset is **100% synthetic**. It is generated mathematically using physics-informed baseline parameters, diurnal periodicity, autoregressive smooth dynamics, and injected anomaly patterns. It **does NOT represent or assume access to real historical Maitri sensor telemetry**.

---

## Purpose
- Provide a clean, reproducible ground-truth dataset for training and benchmarking anomaly detection algorithms.
- Support controlled evaluation of:
  - Statistical Baselines (e.g. Z-score)
  - Deep Learning Models (e.g. LSTM Autoencoder)
  - Threshold selection strategies (dynamic/static percentile-based)
  - Evaluation metrics (Precision, Recall, F1-score, Confusion Matrix)
- Adhere to the **Maitri-First** roadmap before extending to Bharati.

---

## Monitored Sensors & Baseline Profiles

| Sensor ID | Sensor Type | Engineering Unit | Baseline Mean | Diurnal Amplitude | Typical Normal Range |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `TEMP_001` | Temperature | `°C` | -15.0 | 4.5 | -25.0 to -5.0 |
| `PRESS_001` | Pressure | `hPa` | 990.0 | 2.0 | 980.0 to 1005.0 |
| `HUM_001` | Humidity | `%` | 55.0 | 8.0 | 40.0 to 75.0 |
| `VIB_001` | Vibration | `mm/s` | 0.85 | 0.15 | 0.5 to 1.3 |
| `POWER_001`| Power Consumption| `kW` | 35.0 | 6.0 | 25.0 to 48.0 |

---

## Dataset Schema

| Column | Data Type | Description |
| :--- | :--- | :--- |
| `station_id` | String | Antarctic station identifier (`"MTR"` for Maitri) |
| `sensor_id` | String | Unique identifier of the sensor (e.g. `"TEMP_001"`) |
| `timestamp` | ISO-8601 String | UTC timestamp of observation (e.g. `"2026-03-01T00:00:00Z"`) |
| `value` | Float / NaN | Measured numerical value (`NaN` / null during dropout) |
| `unit` | String | Engineering unit of measurement (e.g. `"°C"`, `"kW"`) |
| `quality` | String | Data quality flag: `"GOOD"`, `"BAD"`, or `"MISSING"` |
| `source` | String | Origin identifier (`"SYNTHETIC_ML_DATASET"`) |
| `anomaly_type` | String | Class label: `"NORMAL"`, `"SPIKE"`, `"DRIFT"`, `"DROPOUT"`, `"STUCK_VALUE"` |
| `is_anomaly` | Integer | Binary ground truth label (`0` for normal, `1` for anomalous) |

---

## Anomaly Definitions

1. **NORMAL (`is_anomaly = 0`)**:
   - Follows daily diurnal cycles, physical continuity (AR(1) process), and low-variance Gaussian noise.
   - `quality = "GOOD"`.

2. **SPIKE (`is_anomaly = 1`)**:
   - Short-lived, high-magnitude transient shock or pulse deviating significantly from local mean.
   - `quality = "BAD"`.

3. **DRIFT (`is_anomaly = 1`)**:
   - Continuous progressive deviation or ramp away from the normal baseline, simulating progressive sensor degradation, thermal runaway, or mechanical fatigue.
   - `quality = "BAD"`.

4. **DROPOUT (`is_anomaly = 1`)**:
   - Sensor communication outage or packet loss. Telemetry `value` becomes `NaN` (null) for a contiguous duration.
   - `quality = "MISSING"`.

5. **STUCK_VALUE (`is_anomaly = 1`)**:
   - Sensor freeze / flatline condition where reading remains identically constant across multiple timestamps without natural variation.
   - `quality = "BAD"`.

---

## Split Architecture & Stationary Multi-Cycle Diurnal Design
To ensure fair out-of-sample benchmarking without temporal distribution shifts:
- **Stationary Diurnal Cycles**: Diurnal periods are configured so that multiple full sinusoidal cycles occur across the series (period = 288 samples). This ensures that Training, Validation, and Test partitions all experience equivalent normal baseline distributions (means and variances).
- **Training Partition (0% - 70%)**: Pure normal operational telemetry (7,000 samples total) for baseline fitting and unsupervised autoencoder sequence training.
- **Validation Partition (70% - 85%)**: Balanced partition containing normal telemetry and representative injected anomalies (`SPIKE`, `DRIFT`, `DROPOUT`, `STUCK_VALUE`) for threshold calibration.
- **Test Partition (85% - 100%)**: Untouched benchmark partition containing normal telemetry and independent injected anomalies (`SPIKE`, `DRIFT`, `DROPOUT`, `STUCK_VALUE`) for out-of-sample evaluation.

---

## Reproducibility & Generation

The dataset generator uses NumPy's modern `Generator` seeded deterministically.

### Generate via CLI:
```bash
# Default: 2000 points per sensor (10,000 total rows)
.venv/bin/python ml/data/generate_maitri_dataset.py

# Custom configuration:
.venv/bin/python ml/data/generate_maitri_dataset.py --seed 42 --points-per-sensor 2000 --output ml/data/maitri_synthetic_telemetry.csv
```
