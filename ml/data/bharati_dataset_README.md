# Bharati Synthetic Telemetry Dataset (SIH26060)

**Station Name:** Bharati Indian Antarctic Research Station  
**Station Code:** `BRT`  
**Dataset File:** `bharati_synthetic_telemetry.csv`  
**Dataset Generator:** `generate_bharati_dataset.py`  
**Owner:** Person C (ML Specialist)  
**Dataset Scale:** 10,000 total records (2,000 records per sensor across 5 sensors)  
**Default Seed:** `42`  
**Source Tag:** `SYNTHETIC_ML_DATASET`  

---

> [!IMPORTANT]
> **SYNTHETIC DATASET DISCLAIMER**:
> This dataset contains purely **SYNTHETIC** sensor telemetry generated for machine learning development, baseline modeling, neural network training, threshold calibration, and pipeline testing for the Polarix Antarctic Station Monitoring Platform.
> It does **NOT** use, represent, or claim real historical or live sensor data measured at Bharati station.

---

## 1. Station Overview & Climate Modeling Rationale

Bharati is India's third Antarctic research station, commissioned in 2012 at the Larsemann Hills in East Antarctica ($69^\circ 24' \text{S}, 76^\circ 11' \text{E}$). Situated in a coastal ice-free oasis, its environmental profile features maritime polar dynamics with moderate diurnal fluctuations compared to inland stations.

The synthetic telemetry generator combines:
- Stationary sinusoidal multi-cycle diurnal variation (`day_period = 288` samples $\approx 24$ hours) ensuring balanced statistical envelopes across Train, Validation, and Test splits.
- First-order autoregressive drift ($AR(1)$, $\phi=0.95$) capturing physical thermal, barometric, and mechanical inertia.
- High-frequency Gaussian sensor measurement noise.

---

## 2. Sensor Specifications

| Sensor ID | Monitored Parameter | Unit | Baseline Mean | Diurnal Amplitude | Measurement Noise ($\sigma$) | Physical Bounds |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`BRT_TEMP_001`** | Structural / Ambient Temperature | `C` | $-10.0^\circ\text{C}$ | $3.5^\circ\text{C}$ | $0.30^\circ\text{C}$ | $[-35.0, 15.0]$ |
| **`BRT_PRESS_001`** | Station Barometric Pressure | `hPa` | $985.0\text{ hPa}$ | $2.5\text{ hPa}$ | $0.20\text{ hPa}$ | $[920.0, 1035.0]$ |
| **`BRT_HUM_001`** | Relative Indoor/Outdoor Humidity | `%` | $60.0\%$ | $7.0\%$ | $1.0\%$ | $[15.0, 98.0]$ |
| **`BRT_VIB_001`** | Power Generator Vibration | `mm/s` | $0.75\text{ mm/s}$ | $0.12\text{ mm/s}$ | $0.03\text{ mm/s}$ | $[0.0, 12.0]$ |
| **`BRT_POWER_001`** | Main Station Power Consumption | `kW` | $42.0\text{ kW}$ | $5.5\text{ kW}$ | $0.70\text{ kW}$ | $[10.0, 110.0]$ |

---

## 3. Telemetry Schema

Each record contains the following 9 standardized fields:

| Column Name | Data Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| **`station_id`** | `string` | `"BRT"` | Station identifier code (Bharati). |
| **`sensor_id`** | `string` | `"BRT_TEMP_001"` | Supported Bharati sensor ID. |
| **`timestamp`** | `string` | `"2026-03-01T00:00:00Z"` | ISO 8601 UTC timestamp. |
| **`value`** | `float` or `null` | `-9.45` | Numeric sensor measurement (or null for dropout). |
| **`unit`** | `string` | `"C"` | Measurement unit (`"C"`, `"hPa"`, `"%"`, `"mm/s"`, `"kW"`). |
| **`quality`** | `string` | `"GOOD"` | Telemetry quality flag (`"GOOD"`, `"BAD"`, `"MISSING"`). |
| **`source`** | `string` | `"SYNTHETIC_ML_DATASET"` | Fixed telemetry source tag. |
| **`anomaly_type`** | `string` | `"NORMAL"` | Ground truth anomaly label for offline validation. |
| **`is_anomaly`** | `integer` | `0` | Binary indicator ($0=\text{Normal}, 1=\text{Anomaly}$). |

---

## 4. Anomaly Types & Offline Evaluation Semantics

The dataset incorporates 5 distinct anomaly classifications:

1. **`NORMAL`** ($93.62\%$ of records):
   - Baseline stationary diurnal time-series within nominal operating envelopes.
   - `quality = "GOOD"`, `is_anomaly = 0`.
2. **`SPIKE`** ($0.41\%$ of records):
   - Sudden, short-lived step excursion ($2.5\times$ diurnal amplitude $+ 6.0\sigma$ noise).
   - Injected at $\approx 72\%$ (Validation) and $\approx 87\%$ (Test) partitions.
   - `quality = "BAD"`, `is_anomaly = 1`.
3. **`DRIFT`** ($3.00\%$ of records):
   - Gradual linear ramp away from normal baseline over 25–35 contiguous time steps.
   - Injected at $\approx 75\%$ (Validation, positive ramp) and $\approx 90\%$ (Test, negative ramp).
   - `quality = "BAD"`, `is_anomaly = 1`.
4. **`STUCK_VALUE`** ($2.40\%$ of records):
   - Sensor output frozen at a constant flatline value for 15–25 contiguous time steps.
   - Injected at $\approx 82\%$ (Validation) and $\approx 97\%$ (Test).
   - `quality = "BAD"`, `is_anomaly = 1`.
5. **`DROPOUT`** ($0.57\%$ of records):
   - Telemetry dropout / sensor offline event.
   - `value = np.nan` (missing/null), `quality = "MISSING"`, `is_anomaly = 1`.

---

## 5. Partitioning Strategy for Machine Learning

The dataset is partitioned chronologically to support clean, leakage-free unsupervised modeling:
- **Training Partition ($0\% - 70\%$, 7,000 records)**: 100% pure normal baseline data with zero anomalies, providing clean data for training unsupervised autoencoders and statistical estimators.
- **Validation Partition ($70\% - 85\%$, 1,500 records)**: Contains representative anomalies of all types for tuning decision thresholds and evaluating hyperparameters.
- **Test Partition ($85\% - 100\%$, 1,500 records)**: Held-out untouched partition containing independent anomaly windows for final evaluation.

---

## 6. Generation & Determinism

To regenerate the dataset identically:
```bash
python ml/data/generate_bharati_dataset.py --seed 42 --points-per-sensor 2000 --output ml/data/bharati_synthetic_telemetry.csv
```
The fixed random seed (`42`) guarantees exact bit-for-bit reproducibility.
