# Polarix Canonical Energy ML Dataset Specification

**Project:** Polarix — Smart India Hackathon 2026 (Problem Statement SIH26060)
**Author:** Person C — Machine Learning Specialist
**Module:** `ml/energy/data/`
**Status:** `CANONICAL_SCHEMA_DEFINITION`

---

## 1. Canonical Energy Record Schema

The canonical Energy ML dataset defines a unified, synchronized multi-variable telemetry stream for Indian Antarctic station microgrids (`MTR` and `BRT`).

Every row represents an operational energy snapshot at timestamp $t$:

| Field Name | Type | Physical Unit | Valid Range | Nullable | Provenance Classification | Description |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `timestamp` | `string` | ISO-8601 UTC | `2026-01-01T00:00:00Z`+ | **No** | `SYNTHETIC_TIMELINE` | Synchronized chronological timestamp. |
| `station_id` | `string` | Categorical | `["MTR", "BRT"]` | **No** | `STATION_METADATA` | Identifier for Indian Antarctic station. |
| `power_demand_kw` | `float` | Kilowatts (kW) | $[10.0, 150.0]$ | **No** | `SYNTHETIC_POLARIX_OPERATIONAL` | Total real-time station electrical + thermal base load. |
| `generator_output_kw` | `float` | Kilowatts (kW) | $[0.0, 160.0]$ | **No** | `SYNTHETIC_POLARIX_OPERATIONAL` | Active generation delivered by operational diesel generators. |
| `energy_consumption_kwh` | `float` | Kilowatt-hours (kWh) | $[0.0, 200.0]$ | **No** | `DERIVED_METRIC` | Cumulative energy consumed over the sampling interval. |
| `battery_soc_percent` | `float` | Percentage (%) | $[0.0, 100.0]$ | **No** | `SYNTHETIC_POLARIX_OPERATIONAL` | Battery Energy Storage System (BESS) State-of-Charge. |
| `battery_charge_kw` | `float` | Kilowatts (kW) | $[0.0, 50.0]$ | **No** | `SYNTHETIC_POLARIX_OPERATIONAL` | Power flowing into BESS from surplus generation. |
| `battery_discharge_kw` | `float` | Kilowatts (kW) | $[0.0, 50.0]$ | **No** | `SYNTHETIC_POLARIX_OPERATIONAL` | Power supplied by BESS to support station load. |
| `fuel_consumption_l` | `float` | Liters (L) | $[0.0, 60.0]$ | **No** | `DERIVED_METRIC` | Fuel burned by active generators over sampling interval. |
| `temperature_c` | `float` | Degrees Celsius (°C) | $[-55.0, +15.0]$ | **No** | `REAL_PUBLIC_INDIAN_WEATHER_BOUNDED` | Ambient outdoor temperature influencing heating load. |
| `humidity_percent` | `float` | Percentage (%) | $[10.0, 100.0]$ | **No** | `REAL_PUBLIC_INDIAN_WEATHER_BOUNDED` | Ambient relative humidity at station site. |
| `pressure_hpa` | `float` | Hectopascals (hPa) | $[920.0, 1040.0]$ | **No** | `REAL_PUBLIC_INDIAN_WEATHER_BOUNDED` | Barometric air pressure. |
| `wind_speed_mps` | `float` | Meters/second (m/s) | $[0.0, 65.0]$ | **No** | `REAL_PUBLIC_INDIAN_WEATHER_BOUNDED` | Sustained wind velocity (katabatic wind factor). |
| `sensor_anomaly_score` | `float` | Standardized Score | $[0.0, 500.0]$ | **Yes** | `UPSTREAM_SENSOR_ML_FEATURE` | Composite station anomaly score from Sensor ML V1/V2. |
| `sensor_anomaly_status` | `string` | Categorical | `NORMAL, ANOMALY, ...` | **No** | `UPSTREAM_SENSOR_ML_FEATURE` | Operational state emitted by upstream Sensor ML engine. |
| `sensor_anomaly_type` | `string` | Categorical | `NORMAL, SPIKE, ...` | **Yes** | `UPSTREAM_SENSOR_ML_FEATURE` | Specific failure mode identified by Sensor ML. |
| `source` | `string` | Provenance Tag | `SIMULATOR, PUBLIC_REF` | **No** | `METADATA` | Data origin tag. |
| `data_quality` | `string` | Quality Flag | `GOOD, BAD, UNCERTAIN` | **No** | `METADATA` | Data integrity flag. |

---

## 2. Provenance Taxonomy

1. **`REAL_PUBLIC_INDIAN_WEATHER_BOUNDED`**: Physics and distribution bounds derived from published meteorological records of NCPOR/NPDC Indian Scientific Expeditions to Antarctica (Maitri & Bharati).
2. **`SYNTHETIC_POLARIX_OPERATIONAL`**: Microgrid electrical and battery telemetry generated through thermodynamic building models and generator efficiency curves.
3. **`DERIVED_METRIC`**: Computed directly from physical laws ($E = P \cdot \Delta t$, $F = \text{BSFC} \cdot P \cdot \Delta t$).
4. **`UPSTREAM_SENSOR_ML_FEATURE`**: Telemetry and anomaly predictions passed downstream from the Sensor ML module.
5. **`FUTURE_BACKEND_TELEMETRY`**: Reserved fields for live IoT ingestion when Person A's backend simulator is integrated.

---

## 3. Target Variable Formulations

### Primary Forecasting Targets (Regressors):
1. **`target_power_demand_1h_kw`**: Average station demand over next 1 hour ($t \to t+1\,\text{hr}$).
2. **`target_battery_soc_1h_percent`**: Expected battery state-of-charge at $t+1\,\text{hr}$.
3. **`target_energy_demand_6h_kwh`**: Cumulative energy requirement over next 6 hours ($t \to t+6\,\text{hr}$).
4. **`target_energy_demand_24h_kwh`**: Cumulative day-ahead energy requirement ($t \to t+24\,\text{hr}$).

### Operational Risk Target (Classifier):
5. **`target_energy_deficit_risk`**:
   - `0` (`NORMAL`): Generation capacity + BESS available reserves $\ge 1.30 \times$ peak demand.
   - `1` (`DEFICIT_RISK`): Available power $< 1.10 \times$ peak demand or projected BESS SoC $< 25\%$.

---

## 4. Leakage Prevention & Temporal Split Rules

1. **Strict Chronological Splitting**:
   - Training Partition: First **70%** of sequential timeline.
   - Validation Partition: Next **15%** of sequential timeline.
   - Held-Out Test Partition: Final **15%** of sequential timeline.
2. **Feature Scaler Isolation**: All feature normalization scalers (MinMax, StandardScaler) must be fit exclusively on the training partition.
3. **Causal Lag Windows**: Lagged power demand ($P(t-1), P(t-2), \dots$) and rolling statistics must use observations at or before time $t$ with zero forward lookahead.
