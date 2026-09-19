# Polarix Temperature Forecasting ML Subsystem (`ml/temperature/`)

## 1. Overview & Architectural Role
The **Temperature Forecasting ML Subsystem** is an autonomous, standalone, station-aware machine learning capability designed for the **Polarix Smart Microgrid and Habitat Platform** (SIH 2026, Problem Statement SIH26060, Team Byte Me_26 / 143760).

It provides multi-horizon ambient temperature forecasts for Indian Antarctic research stations:
- **Maitri (`MTR`):** Inland rock oasis microclimate (Schirmacher Oasis, 70.77°S, 11.73°E, elevation 117m).
- **Bharati (`BRT`):** Coastal promontory maritime microclimate (Larsemann Hills, 69.40°S, 76.18°E, elevation 35m).

Forecast horizons:
- **`+1h` (`target_temperature_1h_c`):** Short-term HVAC fine regulation and immediate heat-pump modulation.
- **`+6h` (`target_temperature_6h_c`):** Thermal mass pre-conditioning and diesel generator dispatch staging.
- **`+24h` (`target_temperature_24h_c`):** Day-ahead diurnal habitat thermal budget and energy demand planning.

---

## 2. Relationship to Energy ML & Sensor ML
Polarix maintains a strictly modular subsystem hierarchy:

```
┌────────────────────────────────────────────────────────┐
│                      Sensor ML                         │
│   (V1 / V2 LSTM-Autoencoders: Reconstruction & Health) │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                   Temperature ML                       │
│    (Multi-Horizon LSTM: 1h, 6h, 24h Temp Forecast)     │
└──────────────────────────┬─────────────────────────────┘
                           │ (Environmental Input)
┌──────────────────────────▼─────────────────────────────┐
│                      Energy ML                         │
│  (Power Forecasting, Battery SoC, Deficit-Risk Class)  │
└────────────────────────────────────────────────────────┘
```

### Architectural Separation Guarantees:
1. **Independent Subsystem:** `ml/temperature/` is completely decoupled from `ml/energy/` and `ml/`. It maintains its own data pipeline, models, preprocessing scalers, inference engines, tests, and versioning.
2. **Zero Upstream Dependency:** Maintaining or retraining Temperature ML requires zero edits to Energy ML or Sensor ML codebases.
3. **Downstream Consumption:** Energy ML or habitat HVAC optimization may consume temperature forecasts as causal exogenous inputs, but Temperature ML core training and inference remain self-contained.

---

## 3. Data Provenance & Calibration
- **Provenance Category:** `SYNTHETIC_POLARIX_DATA`
- **Calibration Standards:**
  - **National Centre for Polar and Ocean Research (NCPOR), Ministry of Earth Sciences, Govt of India:** Calibrates empirical temperature ranges, diurnal solar cycles, and barometric variability for Maitri and Bharati.
  - **Australian Antarctic Data Centre (AADC CC BY 4.0):** AWS archive bounds for East Antarctic synoptic storm transitions and katabatic wind speeds.
- **Disclaimer:** All training and evaluation datasets are deterministically generated from physical Antarctic thermodynamic and solar geometry equations conditioned on empirical NCPOR bounds. They are never represented as classified real-time station SCADA telemetry.

---

## 4. Dataset Specification & Feature Set

### 4.1 Canonical Input Telemetry Features ($N=9$)
| Feature Name | Type | Unit | Range / Values | Physical Description |
|---|---|---|---|---|
| `temperature_c` | Float | °C | [-50.0, 15.0] | Ambient 2-meter air temperature |
| `humidity_percent` | Float | % | [10.0, 100.0] | Relative humidity |
| `pressure_hpa` | Float | hPa | [910.0, 1045.0] | Atmospheric barometric pressure |
| `wind_speed_mps` | Float | m/s | [0.0, 65.0] | Sustained 10-meter wind speed |
| `sin_hour`, `cos_hour` | Float | - | [-1.0, 1.0] | Cyclical diurnal hour embeddings |
| `sin_day`, `cos_day` | Float | - | [-1.0, 1.0] | Cyclical annual seasonal embeddings |
| `is_bharati` | Float | - | {0.0, 1.0} | Station identifier indicator (0=MTR, 1=BRT) |

### 4.2 Multi-Horizon Forecasting Targets
- `target_temperature_1h_c` $= \text{temperature}(t + 1\text{h})$
- `target_temperature_6h_c` $= \text{temperature}(t + 6\text{h})$
- `target_temperature_24h_c` $= \text{temperature}(t + 24\text{h})$

---

## 5. Strict Chronological Splits (70 / 15 / 15)
Temporal boundaries are strictly maintained across 8,760 hours/station (17,520 hours combined):

| Split Partition | Time Interval (UTC) | Hours / Station | Ratio | Purpose |
|---|---|---|---|---|
| **TRAIN** | `2026-01-01T00:00:00Z` to `2026-09-13T17:00:00Z` | 6,132 | 70% | Model optimization & Scaler fitting |
| **VALIDATION** | `2026-09-13T18:00:00Z` to `2026-11-07T05:00:00Z` | 1,314 | 15% | Early stopping & hyperparameter selection |
| **TEST** | `2026-11-07T06:00:00Z` to `2026-12-31T23:00:00Z` | 1,314 | 15% | Held-out unbiased benchmark evaluation |

---

## 6. Model Architecture (`temperature_lstm_v1`)
A multi-horizon recurrent neural network implemented in PyTorch:

- **Architecture:** 2-layer LSTM with Linear Feedforward Projection Head
- **Lookback Window:** 24 hours (causal sliding sequence $t-23 \dots t$)
- **Input Dimension:** 9 features
- **Hidden Dimension:** 64 units
- **Dropout:** 0.10
- **Total Parameters:** 54,659 (lightweight, rapid inference on low-power edge nodes)
- **Optimizer:** Adam ($\text{lr} = 0.001$)
- **Loss Function:** Mean Squared Error (MSE)
- **Stopping Strategy:** Early stopping on validation loss (patience = 10 epochs)

---

## 7. Benchmark Evaluation & Baseline Comparison

Evaluated on the held-out **Test Partition** (`2026-11-07T06:00:00Z` to `2026-12-31T23:00:00Z`):

### 7.1 Combined Station Evaluation (MTR + BRT)
| Horizon | Model | MAE (°C) | RMSE (°C) | R² | sMAPE (%) | Improvement vs Persistence | Improvement vs Recent Mean |
|---|---|---|---|---|---|---|---|
| **1h** | **LSTM (v1)** | **1.43** | **1.77** | **0.74** | **0.52%** | *Persistence baseline is lower due to strong 1h auto-correlation (0.68°C)* | **+21.87%** |
| 1h | Persistence | 0.68 | 1.04 | 0.91 | 0.25% | baseline | - |
| 1h | Recent Mean | 1.83 | 2.36 | 0.54 | 0.66% | - | baseline |
| **6h** | **LSTM (v1)** | **1.88** | **2.33** | **0.55** | **0.68%** | **Comparable (-1.35%)** | **+13.76%** |
| 6h | Persistence | 1.86 | 2.45 | 0.50 | 0.67% | baseline | - |
| 6h | Recent Mean | 2.18 | 2.80 | 0.35 | 0.79% | - | baseline |
| **24h** | **LSTM (v1)** | **2.31** | **2.82** | **0.34** | **0.84%** | **+14.76% (Beats Persist)** | **+16.47% (Beats Mean)** |
| 24h | Persistence | 2.71 | 3.55 | -0.04 | 0.98% | baseline | - |
| 24h | Recent Mean | 2.77 | 3.55 | -0.04 | 1.00% | - | baseline |

### 7.2 Empirical Finding on Thermal Autocorrelation
- At the **1-hour horizon**, ambient temperature exhibits extreme autoregressive inertia ($R^2=0.91$ for persistence).
- By the **24-hour horizon**, diurnal and synoptic shifts cause persistence to fail ($R^2 < 0$, MAE $2.71^\circ\text{C}$). The LSTM model significantly outperforms both Persistence (+14.8%) and Recent Mean (+16.5%) with an MAE of **$2.31^\circ\text{C}$**.

---

## 8. Standalone Inference API & Usage

```python
from ml.temperature.inference.temperature_forecaster import TemperatureForecaster
import pandas as pd

# Initialize forecaster (loads weights, config, and scaler)
forecaster = TemperatureForecaster()

# Telemetry DataFrame must contain at least 24 consecutive hourly records
df_window = pd.read_csv("ml/temperature/data/maitri_temperature_telemetry.csv").iloc[:24]

response = forecaster.predict_window(station_id="MTR", df=df_window)
print(response)
```

### Standard JSON Response Contract:
```json
{
  "station_id": "MTR",
  "timestamp": "2026-01-01T23:00:00Z",
  "status": "PREDICTION_AVAILABLE",
  "model_version": "temperature-lstm-v1",
  "forecasts": {
    "temperature_1h_c": -12.45,
    "temperature_6h_c": -11.82,
    "temperature_24h_c": -10.95
  },
  "provenance": {
    "source": "SYNTHETIC_POLARIX_DATA",
    "model_status": "CANDIDATE",
    "disclaimer": "Generated deterministically from physically grounded Antarctic meteorological transfer equations and seasonal solar geometry conditioned on NCPOR empirical bounds."
  }
}
```

### Status Codes:
- `PREDICTION_AVAILABLE`: Forecast successfully generated.
- `INSUFFICIENT_HISTORY`: Less than 24 valid hourly records provided.
- `INVALID_INPUT`: Malformed schema, invalid station ID, time gaps $>1\text{h}$, duplicate timestamps, or NaN/Inf values.

---

## 9. Module Layout
```
ml/temperature/
├── __init__.py
├── README.md
├── data/
│   ├── __init__.py
│   ├── README.md
│   ├── generate_temperature_dataset.py
│   ├── maitri_temperature_telemetry.csv
│   ├── bharati_temperature_telemetry.csv
│   ├── polarix_temperature_telemetry.csv
│   ├── temperature_dataset_manifest.json
│   └── temperature_dataset_spec.json
├── models/
│   ├── __init__.py
│   ├── temperature_lstm.py
│   ├── temperature_lstm_v1.pt
│   ├── temperature_lstm_v1_config.json
│   └── temperature_lstm_v1_scaler.json
├── training/
│   ├── __init__.py
│   ├── baselines.py
│   ├── preprocessing.py
│   └── train_temperature_lstm.py
├── inference/
│   ├── __init__.py
│   └── temperature_forecaster.py
├── evaluation/
│   ├── __init__.py
│   └── evaluate_temperature.py
├── results/
│   ├── temperature_metrics.json
│   ├── temperature_evaluation_report.md
│   ├── temperature_ml_inference_contract.json
│   └── temperature_ml_milestone_manifest.json
└── tests/
    ├── __init__.py
    ├── test_temperature_dataset_spec.py
    ├── test_temperature_dataset_generation.py
    ├── test_temperature_baselines.py
    ├── test_temperature_anti_leakage.py
    └── test_temperature_forecaster.py
```

---

## 10. Verification & Test Suite
Run the Temperature ML test suite:
```bash
PYTHONPATH=. pytest ml/temperature/tests -v
```

Run the complete Polarix ML regression suite:
```bash
PYTHONPATH=. pytest ml/tests ml/energy/tests ml/service/tests ml/temperature/tests -q
```
