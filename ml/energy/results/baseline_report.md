# Polarix Energy ML Forecasting Baseline Report

**Model Version:** `lstm-energy-baseline-v1`
**Evaluation Partition:** Held-Out Test Partition (`2026-11-07T06:00:00Z` $\to$ `2026-12-31T23:00:00Z`, $N=1,314$ hours/station)
**Author:** Person C — Machine Learning Specialist
**Evaluation Date:** 2026-09-19

---

## 1. Executive Summary & Core Findings

This study establishes the initial **Energy ML Forecasting Baseline** for the Polarix microgrid management system. Using a multi-task stacked LSTM architecture trained on 24-hour causal sequences, the model demonstrates clear predictive skill over classical benchmarks across all four forecasting horizons without lookahead data leakage.

### Key Benchmark Comparison (Combined Test Partition):

| Forecasting Task | Target Horizon | Persistence MAE | 24h Seasonal Lag MAE | Neural LSTM MAE | Improvement vs Best Baseline | Neural $R^2$ |
|:---|:---|:---|:---|:---|:---|:---|
| **Task A: Power Demand** | 1-Hour ($t+1$) | $5.17\,\text{kW}$ | $5.63\,\text{kW}$ | **$3.35\,\text{kW}$** | **$+35.1\%$** | **$0.631$** |
| **Task B: Battery SoC** | 1-Hour ($t+1$) | $0.094\,\%$ | $0.137\,\%$ | **$0.067\,\%$** | **$+29.0\%$** | **$0.154$** |
| **Task C: 6h Energy Demand** | 6-Hour ($t+1..t+6$) | $35.01\,\text{kWh}$ | $21.37\,\text{kWh}$ | **$13.46\,\text{kWh}$** | **$+37.0\%$** | **$0.862$** |
| **Task D: 24h Energy Demand** | 24-Hour ($t+1..t+24$) | $151.64\,\text{kWh}$ | $52.29\,\text{kWh}$ | **$41.92\,\text{kWh}$** | **$+18.9\%$** | **$0.862$** |

---

## 2. Station-Disaggregated Performance

### 2.1 Maitri Station (`MTR`) — Inland Oasis Microgrid

| Target Variable | Model | MAE | RMSE | $R^2$ | sMAPE (%) |
|:---|:---|:---|:---|:---|:---|
| **Power Demand (1h)** | Neural LSTM | **$3.36\,\text{kW}$** | **$5.95\,\text{kW}$** | **$0.506$** | **$5.10\%$** |
| | Persistence | $4.95\,\text{kW}$ | $8.17\,\text{kW}$ | $0.057$ | $7.48\%$ |
| | Seasonal 24h Lag | $5.28\,\text{kW}$ | $8.24\,\text{kW}$ | $0.042$ | $7.95\%$ |
| **Battery SoC (1h)** | Neural LSTM | **$0.061\,\%$** | **$0.407\,\%$** | **$0.130$** | **$0.063\%$** |
| | Persistence | $0.083\,\%$ | $0.496\,\%$ | $-0.338$ | $0.087\%$ |
| **Energy Demand (6h)** | Neural LSTM | **$13.61\,\text{kWh}$** | **$17.45\,\text{kWh}$** | **$0.766$** | **$3.51\%$** |
| | Seasonal 24h Lag | $19.85\,\text{kWh}$ | $25.23\,\text{kWh}$ | $0.505$ | $5.11\%$ |
| **Energy Demand (24h)**| Neural LSTM | **$41.82\,\text{kWh}$** | **$52.85\,\text{kWh}$** | **$0.533$** | **$2.68\%$** |
| | Moving Average (24h) | $48.67\,\text{kWh}$ | $60.40\,\text{kWh}$ | $0.401$ | $3.12\%$ |

### 2.2 Bharati Station (`BRT`) — Coastal Promontory Microgrid

| Target Variable | Model | MAE | RMSE | $R^2$ | sMAPE (%) |
|:---|:---|:---|:---|:---|:---|
| **Power Demand (1h)** | Neural LSTM | **$3.35\,\text{kW}$** | **$6.18\,\text{kW}$** | **$0.489$** | **$4.37\%$** |
| | Persistence | $5.38\,\text{kW}$ | $8.95\,\text{kW}$ | $-0.080$ | $6.99\%$ |
| | Seasonal 24h Lag | $5.84\,\text{kW}$ | $8.91\,\text{kW}$ | $-0.069$ | $7.61\%$ |
| **Battery SoC (1h)** | Neural LSTM | **$0.073\,\%$** | **$0.395\,\%$** | **$0.178$** | **$0.075\%$** |
| | Persistence | $0.105\,\%$ | $0.497\,\%$ | $-0.192$ | $0.109\%$ |
| **Energy Demand (6h)** | Neural LSTM | **$13.31\,\text{kWh}$** | **$17.62\,\text{kWh}$** | **$0.755$** | **$2.96\%$** |
| | Seasonal 24h Lag | $22.23\,\text{kWh}$ | $27.54\,\text{kWh}$ | $0.395$ | $4.93\%$ |
| **Energy Demand (24h)**| Neural LSTM | **$42.02\,\text{kWh}$** | **$52.89\,\text{kWh}$** | **$0.340$** | **$2.34\%$** |
| | Moving Average (24h) | $51.79\,\text{kWh}$ | $67.67\,\text{kWh}$ | $-0.032$ | $2.87\%$ |

---

## 3. Operational Regime Analysis

Model error across specific Antarctic operational event types:

| Event Regime | 1h Power Demand MAE | 1h Battery SoC MAE | 6h Energy Demand MAE | 24h Energy Demand MAE |
|:---|:---|:---|:---|:---|
| `NORMAL` | $3.21\,\text{kW}$ | $0.061\,\%$ | $12.87\,\text{kWh}$ | $40.85\,\text{kWh}$ |
| `HIGH_LOAD` | $5.42\,\text{kW}$ | $0.142\,\%$ | $20.31\,\text{kWh}$ | $56.74\,\text{kWh}$ |
| `POWER_CONSTRAINT` | $4.89\,\text{kW}$ | $0.185\,\%$ | $18.94\,\text{kWh}$ | $52.10\,\text{kWh}$ |
| `EXTREME_COLD` | $4.12\,\text{kW}$ | $0.098\,\%$ | $16.45\,\text{kWh}$ | $48.33\,\text{kWh}$ |

---

## 4. Leakage Safeguards & Model Governance

1. **Strict Temporal Separation:** Scalers and neural weights were fit exclusively on training data ($t \le \text{2026-09-13T11:00:00Z}$).
2. **Station Boundary Isolation:** Sequence windows never span across stations.
3. **Causal Inputs:** Temporal sine/cosine transformations and rolling features use backward-looking historical steps only.
4. **Sensor ML Decoupling:** Upstream Sensor ML outputs (`sensor_anomaly_score`, `sensor_anomaly_status`) are consumed strictly as external input features; Sensor ML weights and artifacts remain untouched.
