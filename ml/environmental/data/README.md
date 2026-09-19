# Environmental Forecasting Dataset (`ml/environmental/data/`)

## 1. Overview & Provenance
- **Subsystem:** Polarix Environmental Forecasting ML Subsystem (`ml/environmental/`)
- **Data Provenance Category:** `SYNTHETIC_POLARIX_DATA`
- **Station Scopes:**
  - `MTR`: Maitri Research Station (Schirmacher Oasis, 70.77°S, 11.73°E, elevation 117m)
  - `BRT`: Bharati Research Station (Larsemann Hills, 69.40°S, 76.18°E, elevation 35m)
- **Empirical Calibration:** Grounded in macroscopic physical climate bounds from public archives:
  - National Centre for Polar and Ocean Research (NCPOR), Ministry of Earth Sciences, Govt of India
  - Australian Antarctic Data Centre (AADC CC BY 4.0) AWS Archives
- **Disclaimer:** All dataset files are deterministically synthesized based on Antarctic physical atmospheric transfer equations, barometric cyclonic oscillations, katabatic wind dynamics, and solar geometry conditioned on NCPOR empirical bounds. This dataset is never represented as classified real-time station SCADA telemetry.

---

## 2. Canonical Telemetry Features
Every record contains:
1. `timestamp`: ISO-8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`) at 1-hour resolution.
2. `station_id`: `MTR` or `BRT`.
3. `wind_speed_mps`: Sustained 10-meter wind speed in m/s (0 to 65 m/s).
4. `pressure_hpa`: Atmospheric barometric station pressure in hPa (910 to 1045 hPa).
5. `humidity_percent`: Relative atmospheric humidity in % (10% to 100%).
6. `temperature_c`: Ambient 2-meter air temperature in °C (exogenous input feature).
7. `hour`: Hour of day (0 to 23).
8. `day_of_year`: Day of year (1 to 365).
9. `sin_hour`, `cos_hour`: Cyclical hour embeddings.
10. `sin_day`, `cos_day`: Cyclical annual seasonal embeddings.

---

## 3. Multi-Horizon Forecasting Targets (9 Targets)
All target columns are generated strictly via forward index shifts ($t + k$), with zero future contamination in the feature space:
1. `target_wind_speed_1h_mps` ($t + 1\text{h}$)
2. `target_wind_speed_6h_mps` ($t + 6\text{h}$)
3. `target_wind_speed_24h_mps` ($t + 24\text{h}$)
4. `target_pressure_1h_hpa` ($t + 1\text{h}$)
5. `target_pressure_6h_hpa` ($t + 6\text{h}$)
6. `target_pressure_24h_hpa` ($t + 24\text{h}$)
7. `target_humidity_1h_percent` ($t + 1\text{h}$)
8. `target_humidity_6h_percent` ($t + 6\text{h}$)
9. `target_humidity_24h_percent` ($t + 24\text{h}$)

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
- `environmental_dataset_spec.json`: Machine-readable specification schema.
- `generate_environmental_dataset.py`: Fully deterministic generation script (`seed=42`).
- `maitri_environmental_telemetry.csv`: 8,760 rows for Maitri.
- `bharati_environmental_telemetry.csv`: 8,760 rows for Bharati.
- `polarix_environmental_telemetry.csv`: 17,520 rows combined dataset.
- `environmental_dataset_manifest.json`: Verification hashes and summary statistics.
