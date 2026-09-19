# Polarix Environmental Forecasting ML Subsystem (`ml/environmental/`)

## 1. Overview & Architectural Role
The **Environmental Forecasting ML Subsystem** is an autonomous, standalone, station-aware machine learning capability within the **Polarix Microgrid and Habitat Operating System** (SIH 2026, Problem Statement SIH26060, Team Byte Me_26 / 143760).

It provides multi-target, multi-horizon atmospheric forecasts for Indian Antarctic research stations:
- **Maitri (`MTR`):** Inland rock oasis microclimate (Schirmacher Oasis, 70.77°S, 11.73°E, elevation 117m).
- **Bharati (`BRT`):** Coastal promontory maritime microclimate (Larsemann Hills, 69.40°S, 76.18°E, elevation 35m).

### Forecast Target Variables & Horizons (9 Targets):
1. **Wind Speed (`wind_speed_mps`):**
   - `+1h` (`target_wind_speed_1h_mps`): Immediate wind turbine yaw/pitch control and outdoor safety.
   - `+6h` (`target_wind_speed_6h_mps`): Outdoor traverse safety, storm staging, and renewable dispatch.
   - `+24h` (`target_wind_speed_24h_mps`): Day-ahead blizzard alert and station operations planning.
2. **Barometric Pressure (`pressure_hpa`):**
   - `+1h` (`target_pressure_1h_hpa`): Microbarographic trend tracking.
   - `+6h` (`target_pressure_6h_hpa`): Cyclonic front arrival and depression monitoring.
   - `+24h` (`target_pressure_24h_hpa`): Synoptic Antarctic low-pressure tracking.
3. **Relative Humidity (`humidity_percent`):**
   - `+1h` (`target_humidity_1h_percent`): Habitat indoor moisture/condensation regulation.
   - `+6h` (`target_humidity_6h_percent`): Pre-drying station ventilation and sensor icing mitigation.
   - `+24h` (`target_humidity_24h_percent`): Diurnal humidity cycle forecasting.

---

## 2. Relationship to Temperature ML, Energy ML, & Sensor ML
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
                           │
┌──────────────────────────▼─────────────────────────────┐
│                  Environmental ML                      │
│ (Multi-Target LSTM: Wind Speed, Pressure, Humidity)    │
└──────────────────────────┬─────────────────────────────┘
                           │ (Environmental Exogenous Inputs)
┌──────────────────────────▼─────────────────────────────┐
│                      Energy ML                         │
│  (Power Forecasting, Battery SoC, Deficit-Risk Class)  │
└────────────────────────────────────────────────────────┘
```

### Architectural Separation Guarantees:
1. **Independent Subsystem:** `ml/environmental/` is completely decoupled from `ml/temperature/`, `ml/energy/`, and `ml/`. It maintains its own data pipeline, models, scalers, inference engines, tests, and versioning.
2. **Distinct Target Space:** Environmental ML explicitly excludes temperature from its target outputs to eliminate redundancy with `ml/temperature/`. Temperature is used solely as an input feature because of physical atmospheric coupling.
3. **Downstream Consumption:** Energy ML, logistics planning, and operational risk models consume environmental forecasts as causal exogenous inputs.

---

## 3. Data Provenance & Calibration
- **Provenance Category:** `SYNTHETIC_POLARIX_DATA`
- **Calibration Standards:**
  - **National Centre for Polar and Ocean Research (NCPOR), Ministry of Earth Sciences, Govt of India:** Calibrates empirical wind velocity distributions, barometric pressure cycles, and humidity bounds for Maitri and Bharati.
  - **Australian Antarctic Data Centre (AADC CC BY 4.0):** AWS archive bounds for East Antarctic synoptic cyclonic systems and katabatic wind dynamics.
- **Disclaimer:** All dataset files are deterministically synthesized based on Antarctic physical atmospheric transfer equations, barometric cyclonic oscillations, katabatic wind dynamics, and solar geometry conditioned on NCPOR empirical bounds. This dataset is never represented as classified real-time station SCADA telemetry.

---

## 4. Dataset Specification & Feature Set

### 4.1 Canonical Input Telemetry Features ($N=9$)
| Feature Name | Type | Unit | Range / Values | Physical Description |
|---|---|---|---|---|
| `wind_speed_mps` | Float | m/s | [0.0, 65.0] | Sustained 10-meter wind speed |
| `pressure_hpa` | Float | hPa | [910.0, 1045.0] | Atmospheric barometric pressure |
| `humidity_percent` | Float | % | [10.0, 100.0] | Relative atmospheric humidity |
| `temperature_c` | Float | °C | [-50.0, 15.0] | Ambient 2-meter air temperature (exogenous feature) |
| `sin_hour`, `cos_hour` | Float | - | [-1.0, 1.0] | Cyclical diurnal hour embeddings |
| `sin_day`, `cos_day` | Float | - | [-1.0, 1.0] | Cyclical annual seasonal embeddings |
| `is_bharati` | Float | - | {0.0, 1.0} | Station identifier indicator (0=MTR, 1=BRT) |

### 4.2 Multi-Horizon Forecasting Targets (9 Outputs)
- **Wind Speed:** `target_wind_speed_{1h, 6h, 24h}_mps`
- **Barometric Pressure:** `target_pressure_{1h, 6h, 24h}_hpa`
- **Relative Humidity:** `target_humidity_{1h, 6h, 24h}_percent`

---

## 5. Strict Chronological Splits (70 / 15 / 15)
Temporal boundaries are strictly maintained across 8,760 hours/station (17,520 hours combined):

| Split Partition | Time Interval (UTC) | Hours / Station | Ratio | Purpose |
|---|---|---|---|---|
| **TRAIN** | `2026-01-01T00:00:00Z` to `2026-09-13T17:00:00Z` | 6,132 | 70% | Model optimization & Scaler fitting |
| **VALIDATION** | `2026-09-13T18:00:00Z` to `2026-11-07T05:00:00Z` | 1,314 | 15% | Early stopping & hyperparameter selection |
| **TEST** | `2026-11-07T06:00:00Z` to `2026-12-31T23:00:00Z` | 1,314 | 15% | Held-out unbiased benchmark evaluation |

---

## 6. Model Architecture (`environmental_lstm_v1`)
A multi-target multi-horizon recurrent neural network implemented in PyTorch:

- **Architecture:** 2-layer LSTM with Linear Feedforward Projection Head
- **Lookback Window:** 24 hours (causal sliding sequence $t-23 \dots t$)
- **Input Dimension:** 9 features
- **Hidden Dimension:** 64 units
- **Output Dimension:** 9 targets (3 variables × 3 horizons)
- **Dropout:** 0.10
- **Total Parameters:** 56,041 (lightweight, rapid inference on edge hardware)
- **Optimizer:** Adam ($\text{lr} = 0.001$)
- **Loss Function:** Mean Squared Error (MSE)
- **Stopping Strategy:** Early stopping on validation loss (patience = 10 epochs)

---

## 7. Benchmark Evaluation & Baseline Comparison

Evaluated on the held-out **Test Partition** (`2026-11-07T06:00:00Z` to `2026-12-31T23:00:00Z`, $N=2,628$ combined):

### 7.1 Combined Station Evaluation (MTR + BRT)
| Variable | Horizon | Model | MAE | RMSE | R² | vs Persistence MAE | vs Recent Mean MAE |
|---|---|---|---|---|---|---|---|
| **Wind Speed (m/s)** | **1h** | **LSTM (v1)** | **2.00** | **2.80** | **0.83** | **+16.20% (Beats Persist)** | **+36.34% (Beats Mean)** |
| Wind Speed (m/s) | 1h | Persistence | 2.39 | 3.17 | 0.78 | baseline | - |
| Wind Speed (m/s) | 1h | Recent Mean | 3.14 | 4.80 | 0.50 | - | baseline |
| **Wind Speed (m/s)** | **6h** | **LSTM (v1)** | **2.54** | **3.98** | **0.65** | **+13.66% (Beats Persist)** | **+33.79% (Beats Mean)** |
| Wind Speed (m/s) | 6h | Persistence | 2.94 | 4.44 | 0.57 | baseline | - |
| Wind Speed (m/s) | 6h | Recent Mean | 3.83 | 5.89 | 0.24 | - | baseline |
| **Wind Speed (m/s)** | **24h** | **LSTM (v1)** | **3.97** | **6.30** | **0.14** | **+25.32% (Beats Persist)** | **+31.82% (Beats Mean)** |
| Wind Speed (m/s) | 24h | Persistence | 5.31 | 7.94 | -0.37 | baseline | - |
| Wind Speed (m/s) | 24h | Recent Mean | 5.82 | 8.57 | -0.59 | - | baseline |
| **Pressure (hPa)** | **1h** | **LSTM (v1)** | **2.05** | **2.69** | **0.95** | *Persistence is lower (1.56 hPa, R²=0.97)* | **+68.73% (Beats Mean)** |
| Pressure (hPa) | 1h | Persistence | 1.56 | 1.96 | 0.97 | baseline | - |
| Pressure (hPa) | 1h | Recent Mean | 6.56 | 8.11 | 0.51 | - | baseline |
| **Pressure (hPa)** | **6h** | **LSTM (v1)** | **4.17** | **5.19** | **0.80** | **+6.08% (Beats Persist)** | **+51.43% (Beats Mean)** |
| Pressure (hPa) | 6h | Persistence | 4.43 | 5.53 | 0.77 | baseline | - |
| Pressure (hPa) | 6h | Recent Mean | 8.58 | 10.56 | 0.17 | - | baseline |
| **Pressure (hPa)** | **24h** | **LSTM (v1)** | **7.93** | **9.80** | **0.28** | **+32.10% (Beats Persist)** | **+41.26% (Beats Mean)** |
| Pressure (hPa) | 24h | Persistence | 11.68 | 14.30 | -0.53 | baseline | - |
| Pressure (hPa) | 24h | Recent Mean | 13.50 | 16.20 | -0.97 | - | baseline |
| **Humidity (%)** | **1h** | **LSTM (v1)** | **4.44** | **5.59** | **0.83** | **+22.65% (Beats Persist)** | **+42.60% (Beats Mean)** |
| Humidity (%) | 1h | Persistence | 5.73 | 7.22 | 0.71 | baseline | - |
| Humidity (%) | 1h | Recent Mean | 7.73 | 9.65 | 0.49 | - | baseline |
| **Humidity (%)** | **6h** | **LSTM (v1)** | **5.73** | **7.21** | **0.72** | **+17.88% (Beats Persist)** | **+39.85% (Beats Mean)** |
| Humidity (%) | 6h | Persistence | 6.98 | 8.78 | 0.58 | baseline | - |
| Humidity (%) | 6h | Recent Mean | 9.53 | 11.84 | 0.23 | - | baseline |
| **Humidity (%)** | **24h** | **LSTM (v1)** | **9.07** | **11.20** | **0.33** | **+30.51% (Beats Persist)** | **+35.51% (Beats Mean)** |
| Humidity (%) | 24h | Persistence | 13.05 | 16.12 | -0.39 | baseline | - |
| Humidity (%) | 24h | Recent Mean | 14.06 | 17.08 | -0.57 | - | baseline |

---

## 8. Standalone Inference API & Usage

```python
from ml.environmental.inference.environmental_forecaster import EnvironmentalForecaster
import pandas as pd

# Initialize forecaster (loads weights, config, and scaler)
forecaster = EnvironmentalForecaster()

# Telemetry DataFrame must contain at least 24 consecutive hourly records
df_window = pd.read_csv("ml/environmental/data/maitri_environmental_telemetry.csv").iloc[:24]

response = forecaster.predict_window(station_id="MTR", df=df_window)
print(response)
```

### Standard JSON Response Contract:
```json
{
  "station_id": "MTR",
  "timestamp": "2026-01-01T23:00:00Z",
  "status": "PREDICTION_AVAILABLE",
  "model_version": "environmental-lstm-v1",
  "forecasts": {
    "wind_speed_mps": {
      "1h": 8.52,
      "6h": 9.18,
      "24h": 10.45
    },
    "pressure_hpa": {
      "1h": 984.8,
      "6h": 983.2,
      "24h": 979.6
    },
    "humidity_percent": {
      "1h": 61.4,
      "6h": 63.8,
      "24h": 67.2
    }
  },
  "provenance": {
    "source": "SYNTHETIC_POLARIX_DATA",
    "model_status": "CANDIDATE",
    "disclaimer": "Generated deterministically from physically grounded Antarctic atmospheric transfer equations and seasonal solar geometry conditioned on NCPOR empirical bounds."
  }
}
```

---

## 9. Module Layout
```
ml/environmental/
├── __init__.py
├── README.md
├── data/
│   ├── __init__.py
│   ├── README.md
│   ├── generate_environmental_dataset.py
│   ├── maitri_environmental_telemetry.csv
│   ├── bharati_environmental_telemetry.csv
│   ├── polarix_environmental_telemetry.csv
│   ├── environmental_dataset_manifest.json
│   └── environmental_dataset_spec.json
├── models/
│   ├── __init__.py
│   ├── environmental_lstm.py
│   ├── environmental_lstm_v1.pt
│   ├── environmental_lstm_v1_config.json
│   └── environmental_lstm_v1_scaler.json
├── training/
│   ├── __init__.py
│   ├── baselines.py
│   ├── preprocessing.py
│   └── train_environmental_lstm.py
├── inference/
│   ├── __init__.py
│   └── environmental_forecaster.py
├── evaluation/
│   ├── __init__.py
│   └── evaluate_environmental.py
├── results/
│   ├── environmental_metrics.json
│   ├── environmental_evaluation_report.md
│   ├── environmental_ml_inference_contract.json
│   └── environmental_ml_milestone_manifest.json
└── tests/
    ├── __init__.py
    ├── test_environmental_dataset_spec.py
    ├── test_environmental_dataset_generation.py
    ├── test_environmental_baselines.py
    ├── test_environmental_anti_leakage.py
    └── test_environmental_forecaster.py
```

---

## 10. Verification & Test Suite
Run the Environmental ML test suite:
```bash
PYTHONPATH=. pytest ml/environmental/tests -v
```

Run the complete Polarix ML regression suite:
```bash
PYTHONPATH=. pytest ml/tests ml/energy/tests ml/service/tests ml/temperature/tests ml/environmental/tests -q
```
