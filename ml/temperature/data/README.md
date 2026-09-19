# Temperature Forecasting Dataset

## 1. Overview & Provenance
- **Subsystem:** Polarix Temperature Forecasting ML Subsystem (`ml/temperature/`)
- **Data Provenance Category:** `SYNTHETIC_POLARIX_DATA`
- **Station Scopes:**
  - `MTR`: Maitri Research Station (Schirmacher Oasis, 70.77°S, 11.73°E, elevation 117m)
  - `BRT`: Bharati Research Station (Larsemann Hills, 69.40°S, 76.18°E, elevation 35m)
- **Empirical Calibration:** Grounded in macroscopic physical climate envelopes from public archives:
  - National Centre for Polar and Ocean Research (NCPOR), Ministry of Earth Sciences, Govt of India
  - Australian Antarctic Data Centre (AADC CC BY 4.0) AWS Archives
- **Disclaimer:** All dataset files are deterministically synthesized based on Antarctic physical thermodynamics, solar elevation geometry, synoptic barometric fluctuations, katabatic winds, and thermal inertia equations. This dataset is never represented as classified real-time station SCADA telemetry.

---

## 2. Canonical Telemetry Features
Every record contains:
1. `timestamp`: ISO-8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`) at 1-hour resolution.
2. `station_id`: `MTR` or `BRT`.
3. `temperature_c`: Ambient 2-meter air temperature in °C.
4. `humidity_percent`: Relative humidity (10% to 100%).
5. `pressure_hpa`: Barometric station pressure (910 to 1045 hPa).
6. `wind_speed_mps`: 10-meter sustained wind speed (0 to 65 m/s).
7. `hour`: Hour of day (0 to 23).
8. `day_of_year`: Day of year (1 to 365).
9. `sin_hour`, `cos_hour`: Cyclical hour embeddings.
10. `sin_day`, `cos_day`: Cyclical annual seasonal embeddings.

---

## 3. Multi-Horizon Forecasting Targets
All target columns are generated strictly via forward index shifts ($t + k$), with zero future contamination in the feature space:
1. `target_temperature_1h_c` ($t + 1\text{h}$): Short-term thermal adjustment.
2. `target_temperature_6h_c` ($t + 6\text{h}$): Medium-term thermal mass & generator staging horizon.
3. `target_temperature_24h_c` ($t + 24\text{h}$): Day-ahead diurnal habitat planning.

---

## 4. Strict Chronological Splits (70 / 15 / 15)
Total duration: 365 days / 8,760 hours per station (17,520 hours combined).

| Partition | Time Range (UTC) | Hours / Station | Ratio | Purpose |
|---|---|---|---|---|
| **TRAIN** | `2026-01-01T00:00:00Z` to `2026-09-13T17:00:00Z` | 6,132 | 70% | Model parameter optimization & Scaler fitting |
| **VALIDATION** | `2026-09-13T18:00:00Z` to `2026-11-07T05:00:00Z` | 1,314 | 15% | Early stopping & hyperparameter selection |
| **TEST** | `2026-11-07T06:00:00Z` to `2026-12-31T23:00:00Z` | 1,314 | 15% | Unbiased final generalization benchmarking |

---

## 5. File Manifest
- `temperature_dataset_spec.json`: Machine-readable specification schema.
- `generate_temperature_dataset.py`: Fully deterministic generation script (`seed=42`).
- `maitri_temperature_telemetry.csv`: 8,760 rows for Maitri.
- `bharati_temperature_telemetry.csv`: 8,760 rows for Bharati.
- `polarix_temperature_telemetry.csv`: 17,520 rows combined dataset.
- `temperature_dataset_manifest.json`: Verification hashes and summary statistics.
