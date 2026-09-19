# Polarix Environmental Forecasting ML Evaluation Report

## 1. Executive Summary
- **Model Version:** `environmental-lstm-v1`
- **Subsystem:** `Environmental Forecasting ML Subsystem` (Independent Standalone Module)
- **Data Provenance:** `SYNTHETIC_POLARIX_DATA`
- **Evaluation Split:** `TEST (2026-11-07T06:00:00Z to 2026-12-31T23:00:00Z)`

## 2. Multi-Target Multi-Horizon Test Partition Benchmarks

### 2.1 Wind Speed (m/s) — Combined Station Evaluation (MTR + BRT)
| Horizon | Model | MAE | RMSE | R² | sMAPE (%) | vs Persistence MAE | vs Recent Mean MAE |
|---|---|---|---|---|---|---|---|
| **1h** | **LSTM (v1)** | **1.9992** | **2.8028** | **0.8285** | **21.5476** | **+16.2%** | **+36.34%** |
| 1h | Persistence | 2.3856 | 3.1717 | 0.7803 | 27.1524 | baseline | - |
| 1h | Recent Mean | 3.1406 | 4.7996 | 0.4969 | 30.7038 | - | baseline |
| **6h** | **LSTM (v1)** | **2.5379** | **3.9837** | **0.6532** | **25.0989** | **+13.66%** | **+33.79%** |
| 6h | Persistence | 2.9395 | 4.436 | 0.57 | 31.3905 | baseline | - |
| 6h | Recent Mean | 3.833 | 5.8894 | 0.242 | 35.9725 | - | baseline |
| **24h** | **LSTM (v1)** | **3.9674** | **6.2952** | **0.1394** | **36.5505** | **+25.32%** | **+31.82%** |
| 24h | Persistence | 5.3122 | 7.9442 | -0.3705 | 49.2188 | baseline | - |
| 24h | Recent Mean | 5.8187 | 8.5691 | -0.5946 | 50.1099 | - | baseline |

### 2.2 Barometric Pressure (hPa) — Combined Station Evaluation (MTR + BRT)
| Horizon | Model | MAE | RMSE | R² | sMAPE (%) | vs Persistence MAE | vs Recent Mean MAE |
|---|---|---|---|---|---|---|---|
| **1h** | **LSTM (v1)** | **2.0496** | **2.6862** | **0.9465** | **0.2071** | **-31.8%** | **+68.73%** |
| 1h | Persistence | 1.5551 | 1.956 | 0.9716 | 0.1572 | baseline | - |
| 1h | Recent Mean | 6.5554 | 8.1068 | 0.5129 | 0.6618 | - | baseline |
| **6h** | **LSTM (v1)** | **4.1652** | **5.1895** | **0.7989** | **0.4208** | **+6.08%** | **+51.43%** |
| 6h | Persistence | 4.4349 | 5.5284 | 0.7718 | 0.448 | baseline | - |
| 6h | Recent Mean | 8.5753 | 10.5553 | 0.1681 | 0.8656 | - | baseline |
| **24h** | **LSTM (v1)** | **7.9297** | **9.8013** | **0.2806** | **0.8007** | **+32.1%** | **+41.26%** |
| 24h | Persistence | 11.679 | 14.2981 | -0.531 | 1.1789 | baseline | - |
| 24h | Recent Mean | 13.5005 | 16.2031 | -0.9661 | 1.3631 | - | baseline |

### 2.3 Relative Humidity (%) — Combined Station Evaluation (MTR + BRT)
| Horizon | Model | MAE | RMSE | R² | sMAPE (%) | vs Persistence MAE | vs Recent Mean MAE |
|---|---|---|---|---|---|---|---|
| **1h** | **LSTM (v1)** | **4.4356** | **5.5887** | **0.8289** | **6.7241** | **+22.65%** | **+42.6%** |
| 1h | Persistence | 5.7345 | 7.221 | 0.7143 | 8.7149 | baseline | - |
| 1h | Recent Mean | 7.7278 | 9.6467 | 0.4902 | 11.7722 | - | baseline |
| **6h** | **LSTM (v1)** | **5.7307** | **7.2131** | **0.7157** | **8.6817** | **+17.88%** | **+39.85%** |
| 6h | Persistence | 6.9783 | 8.7754 | 0.5792 | 10.5784 | baseline | - |
| 6h | Recent Mean | 9.528 | 11.8382 | 0.2342 | 14.497 | - | baseline |
| **24h** | **LSTM (v1)** | **9.0662** | **11.1971** | **0.3272** | **13.7727** | **+30.51%** | **+35.51%** |
| 24h | Persistence | 13.0462 | 16.1191 | -0.3942 | 19.7993 | baseline | - |
| 24h | Recent Mean | 14.058 | 17.0845 | -0.5662 | 21.1668 | - | baseline |

## 3. Station-Specific Performance Summary

### 3.1 Maitri Station (MTR - Inland Oasis)
| Variable | Horizon | LSTM MAE | Persist MAE | Mean MAE | LSTM R² |
|---|---|---|---|---|---|
| Wind Speed (m/s) | 1h | 2.0631 | 2.3725 | 3.3611 | 0.8328 |
| Wind Speed (m/s) | 6h | 2.7104 | 3.0167 | 4.1614 | 0.6498 |
| Wind Speed (m/s) | 24h | 4.3602 | 5.7685 | 6.4807 | 0.1309 |
| Barometric Pressure (hPa) | 1h | 1.971 | 1.5758 | 6.315 | 0.9454 |
| Barometric Pressure (hPa) | 6h | 4.0573 | 4.4057 | 8.2533 | 0.769 |
| Barometric Pressure (hPa) | 24h | 7.8768 | 11.2601 | 13.0092 | 0.1891 |
| Relative Humidity (%) | 1h | 4.5752 | 6.0556 | 8.3236 | 0.8065 |
| Relative Humidity (%) | 6h | 6.1052 | 7.3509 | 10.2511 | 0.656 |
| Relative Humidity (%) | 24h | 9.8834 | 14.0508 | 15.3097 | 0.1582 |

### 3.2 Bharati Station (BRT - Coastal Promontory)
| Variable | Horizon | LSTM MAE | Persist MAE | Mean MAE | LSTM R² |
|---|---|---|---|---|---|
| Wind Speed (m/s) | 1h | 1.9353 | 2.3987 | 2.9201 | 0.8193 |
| Wind Speed (m/s) | 6h | 2.3654 | 2.8623 | 3.5046 | 0.6496 |
| Wind Speed (m/s) | 24h | 3.5746 | 4.8558 | 5.1566 | 0.1262 |
| Barometric Pressure (hPa) | 1h | 2.1283 | 1.5344 | 6.7958 | 0.9336 |
| Barometric Pressure (hPa) | 6h | 4.2732 | 4.4641 | 8.8973 | 0.7748 |
| Barometric Pressure (hPa) | 24h | 7.9827 | 12.0979 | 13.9918 | 0.2011 |
| Relative Humidity (%) | 1h | 4.296 | 5.4133 | 7.132 | 0.7544 |
| Relative Humidity (%) | 6h | 5.3563 | 6.6058 | 8.8049 | 0.6203 |
| Relative Humidity (%) | 24h | 8.2489 | 12.0416 | 12.8063 | 0.1129 |

## 4. Anti-Leakage & Causality Guarantees
- **Strict Chronological Boundaries:** Train (70%), Validation (15%), Test (15%). No temporal shuffling.
- **Feature Normalization:** Scaler fitted exclusively on Train split.
- **Future Mutation Immunity:** Current prediction is strictly invariant to future telemetry perturbations.