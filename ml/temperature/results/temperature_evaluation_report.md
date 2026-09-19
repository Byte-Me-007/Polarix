# Polarix Temperature Forecasting ML Evaluation Report

## 1. Executive Summary
- **Model Version:** `temperature-lstm-v1`
- **Subsystem:** `Temperature Forecasting ML Subsystem` (Independent Standalone Module)
- **Data Provenance:** `SYNTHETIC_POLARIX_DATA`
- **Evaluation Split:** `TEST (2026-11-07T06:00:00Z to 2026-12-31T23:00:00Z)`

## 2. Multi-Horizon Test Partition Benchmarks

### 2.1 Combined Station Evaluation (MTR + BRT)
| Horizon | Model | MAE (°C) | RMSE (°C) | R² | sMAPE (%) | vs Persistence MAE | vs Recent Mean MAE |
|---|---|---|---|---|---|---|---|
| **1h** | **LSTM (v1)** | **1.4283** | **1.7656** | **0.7412** | **0.5168** | **+-109.95%** | **+21.87%** |
| 1h | Persistence | 0.6803 | 1.0435 | 0.9096 | 0.2462 | baseline | - |
| 1h | Recent Mean | 1.828 | 2.3582 | 0.5383 | 0.661 | - | baseline |
| **6h** | **LSTM (v1)** | **1.8803** | **2.3264** | **0.5518** | **0.6797** | **+-1.35%** | **+13.76%** |
| 6h | Persistence | 1.8553 | 2.45 | 0.503 | 0.6712 | baseline | - |
| 6h | Recent Mean | 2.1802 | 2.7968 | 0.3523 | 0.7883 | - | baseline |
| **24h** | **LSTM (v1)** | **2.3137** | **2.8215** | **0.3434** | **0.8363** | **+14.76%** | **+16.47%** |
| 24h | Persistence | 2.7143 | 3.5485 | -0.0386 | 0.9813 | baseline | - |
| 24h | Recent Mean | 2.7699 | 3.5479 | -0.0382 | 1.0011 | - | baseline |

### 2.2 Maitri Station (MTR - Inland Oasis)
| Horizon | Model | MAE (°C) | RMSE (°C) | R² | sMAPE (%) | Improvement vs Baseline |
|---|---|---|---|---|---|---|
| **1h** | **LSTM (v1)** | **1.4232** | **1.7574** | **0.7359** | **0.5149** | **+-116.09% vs Persist (0.6586°C)** |
| **6h** | **LSTM (v1)** | **1.8426** | **2.2494** | **0.5693** | **0.666** | **+-1.54% vs Persist (1.8146°C)** |
| **24h** | **LSTM (v1)** | **2.2808** | **2.7461** | **0.3661** | **0.8245** | **+14.87% vs Persist (2.6793°C)** |

### 2.3 Bharati Station (BRT - Coastal Promontory)
| Horizon | Model | MAE (°C) | RMSE (°C) | R² | sMAPE (%) | Improvement vs Baseline |
|---|---|---|---|---|---|---|
| **1h** | **LSTM (v1)** | **1.4333** | **1.7736** | **0.742** | **0.5187** | **+-104.17% vs Persist (0.702°C)** |
| **6h** | **LSTM (v1)** | **1.918** | **2.401** | **0.5285** | **0.6934** | **+-1.17% vs Persist (1.8959°C)** |
| **24h** | **LSTM (v1)** | **2.3465** | **2.8948** | **0.3144** | **0.848** | **+14.65% vs Persist (2.7492°C)** |

## 3. Extreme Cold Scenario Performance
Evaluated on the coldest 15% periods within the held-out test partition:

- **Maitri Extreme Cold Threshold:** $\le -0.18^\circ\text{C}$ ($N=192$)
- **Bharati Extreme Cold Threshold:** $\le -0.62^\circ\text{C}$ ($N=192$)

## 4. Anti-Leakage & Causality Guarantees
- **Chronological Boundaries:** Train (0-70%), Validation (70-85%), Test (85-100%). No temporal shuffling.
- **Feature Normalization:** Scaler fitted exclusively on Train split.
- **Future Mutation Immunity:** Current prediction is strictly invariant to future telemetry perturbations.