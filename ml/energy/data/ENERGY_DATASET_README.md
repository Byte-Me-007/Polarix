# Polarix Energy ML Dataset Documentation

**Project:** Polarix (Smart India Hackathon 2026 — Problem Statement SIH26060, Team Byte Me_26 / 143760)
**Subsystem:** Energy Forecasting & Microgrid Optimization
**Author:** Person C — Machine Learning Specialist
**Dataset Version:** 1.0.0
**Generated Date:** 2026-09-19

---

## 1. Overview & Provenance Disclaimer

> [!IMPORTANT]
> **Strict Provenance Truth & Synthetic Data Disclaimer:**
> Real-time sub-hourly or hourly microgrid telemetry (load profiles, generator loading ratios, battery state of charge, and instantaneous fuel burn rates) for Indian Antarctic research stations (*Maitri* and *Bharati*) is classified operational infrastructure data and is **not published** in public open-access repositories.
>
> To guarantee maximum physical realism without fabricating unverified operational telemetry, the Polarix Energy dataset (`SYNTHETIC_POLARIX_OPERATIONAL_DATA`) is generated from **physically grounded microgrid differential equations and thermodynamic models**. These models are strictly bounded and calibrated using **public scientific Antarctic datasets** (Australian Antarctic Data Centre CC BY 4.0 monthly macro-benchmarks and NCPOR Indian Scientific Expeditions to Antarctica AWS meteorological archives). We **never** claim synthetic operational records are real historical station SCADA logs.

---

## 2. Public Data Calibration & Reference Role

The synthetic dataset synthesizes two primary public Antarctic reference bodies:

1. **AADC Monthly Electrical Energy Benchmark (`AADC_ELEC_1993_2016`):**
   - Source: Australian Antarctic Data Centre (Casey, Davis, Mawson, Macquarie Island).
   - Calibration Role: Macro-level seasonal electrical energy consumption envelopes (winter polar night heating surges vs. summer baseline operations).
2. **NCPOR / NPDC Antarctic Weather Archives (`NCPOR_NPDC_MET_MAITRI_BHARATI`):**
   - Source: National Centre for Polar and Ocean Research, Ministry of Earth Sciences, India.
   - Calibration Role: Valid physical ranges for ambient outdoor air temperature ($-50^\circ\text{C}$ to $+8^\circ\text{C}$), barometric pressure ($925\,\text{hPa}$ to $1035\,\text{hPa}$), relative humidity ($15\%$ to $98\%$), and katabatic blizzard wind gusts up to $62\,\text{m/s}$.

---

## 3. Physical Modeling & Mathematical Equations

The hourly simulation advances deterministically across an 8,760-hour (365-day) timeline for each station using the following coupled governing equations:

### 3.1 Environmental Thermodynamics & Weather Coupling
- **Annual Solar / Thermal Angle:**
  $$\theta_{\text{season}}(t) = 2\pi \frac{\text{day}(t) - 15}{365.25}$$
  where $\theta = 0$ corresponds to mid-summer (January) and $\theta = \pi$ represents the Austral winter solstice (polar night).
- **Ambient Temperature:**
  $$T_{\text{ambient}}(t) = \bar{T}_{\text{mean}} + \Delta T_{\text{season}} \cos(\theta_{\text{season}}(t)) + A_{\text{diurnal}}(t)\sin\left(2\pi \frac{\text{hour}(t)-8}{24}\right) + \epsilon_T(t)$$
  $$\epsilon_T(t) = 0.94 \cdot \epsilon_T(t-1) + \eta_T(t), \quad \eta_T \sim \mathcal{N}(0, 1.2)$$
  with diurnal oscillation dampened during polar night.
- **Correlated Katabatic Wind & Pressure:**
  $$v_{\text{wind}}(t) = v_{\text{base}} + \Delta v_{\text{season}}(t) + \epsilon_{\text{wind}}(t), \quad \epsilon_{\text{wind}}(t) = 0.88 \epsilon_{\text{wind}}(t-1) + 0.12 \text{Exp}(\lambda_{\text{gust}})$$
  $$P_{\text{baro}}(t) = 988.0 - 0.45 v_{\text{wind}}(t) + \mathcal{N}(0, 3.5)$$

### 3.2 Station Microgrid Electrical & Thermal Demand
The instantaneous power demand $P_{\text{demand}}(t)$ combines base life-support, diurnal human activity, building envelope thermal loss, and operational event increments:
$$P_{\text{demand}}(t) = P_{\text{base}} + P_{\text{crew}}(t) + Q_{\text{thermal}}(t) + \Delta P_{\text{event}}(t) + \mathcal{N}(0, \sigma_{\text{noise}})$$
where the building heat loss $Q_{\text{thermal}}$ satisfies:
$$Q_{\text{thermal}}(t) = k_{\text{thermal}} \max(0, 18.0 - T_{\text{ambient}}(t)) + 0.22 v_{\text{wind}}(t)\left(\frac{\max(0, 18.0 - T_{\text{ambient}}(t))}{30.0}\right)$$

### 3.3 Battery Energy Storage System (BESS) Dynamics
The discrete-time State-of-Charge (SoC) evolution obeys:
$$\text{SoC}(t+1) = \text{SoC}(t) + \left( P_{\text{charge}}(t) \cdot \eta_{\text{chg}} - \frac{P_{\text{discharge}}(t)}{\eta_{\text{dis}}} \right) \frac{\Delta t}{E_{\text{capacity}}} \times 100\%$$
Subject to strict physical constraints:
- **State Limits:** $\text{SoC}_{\min} \le \text{SoC}(t) \le \text{SoC}_{\max}$ (where $\text{SoC}_{\min}=15\%$, $\text{SoC}_{\max}=98\%$).
- **Power Rating Limits:** $0 \le P_{\text{charge}}(t) \le P_{\text{BESS,max}}$, $0 \le P_{\text{discharge}}(t) \le P_{\text{BESS,max}}$.
- **Mutual Exclusivity Invariant:** $P_{\text{charge}}(t) \cdot P_{\text{discharge}}(t) = 0$ (simultaneous charge and discharge is physically forbidden).

### 3.4 Diesel Generator Loading & Fuel Consumption
Generator output $P_{\text{gen}}(t)$ follows station load with spinning reserve and minimum loading constraints (to prevent exhaust wet-stacking):
$$P_{\text{gen}}(t) \ge P_{\text{rated}} \times \text{Ratio}_{\min} \quad (\text{Ratio}_{\min} = 0.30)$$
Instantaneous diesel fuel burn $F(t)$ (liters/hour) is computed via Brake Specific Fuel Consumption (BSFC) quadratic regression:
$$F(t) = a_0 + a_1 P_{\text{gen}}(t) + a_2 P_{\text{gen}}(t)^2, \quad F(t) \ge 0$$
- Maitri Parameters: $a_0 = 1.85, a_1 = 0.238, a_2 = 0.00015$
- Bharati Parameters: $a_0 = 2.15, a_1 = 0.242, a_2 = 0.00012$

---

## 4. Operational Event Taxonomy

The dataset incorporates 5 distinct operational and climatic event categories:

| Event Type | Trigger / Mechanism | Electrical / Operational Impact |
|:---|:---|:---|
| `NORMAL` | Standard microgrid diurnal baseline | Standard load profile ($35$–$55\,\text{kW}$ MTR, $45$–$75\,\text{kW}$ BRT) |
| `STORM` | Severe katabatic blizzard ($v_{\text{wind}} > 28\,\text{m/s}, P_{\text{baro}} < 970\,\text{hPa}$) | $+18\,\text{kW}$ thermal de-icing & trace heating load |
| `EXTREME_COLD` | Deep winter polar night ($T_{\text{ambient}} < -34^\circ\text{C}$) | $+22\,\text{kW}$ high-capacity HVAC heating |
| `HIGH_LOAD` | Scheduled scientific campaigns / radar / satellite downlink | $+25\,\text{kW}$ pulsed mission payload load |
| `POWER_CONSTRAINT`| Generator maintenance or intake filter servicing | $-15\,\text{kW}$ non-critical load shedding; BESS peak shave |

---

## 5. Canonical Dataset Schema (18 Canonical Fields + Targets)

| Field Name | Type | Unit | Range / Values | Description |
|:---|:---|:---|:---|:---|
| `timestamp` | ISO-8601 string | UTC | `2026-01-01T00:00:00Z` .. `2026-12-31T23:00:00Z` | Synchronized hourly timestamp |
| `station_id` | string | Cat | `MTR`, `BRT` | Station identifier |
| `power_demand_kw` | float | kW | $[10.0, 150.0]$ | Total microgrid electrical load |
| `generator_output_kw`| float | kW | $[0.0, 160.0]$ | Active diesel generator output |
| `energy_consumption_kwh`| float | kWh | $[10.0, 150.0]$ | Integrated hourly energy consumption |
| `battery_soc_percent`| float | % | $[0.0, 100.0]$ | BESS State-of-Charge |
| `battery_charge_kw` | float | kW | $[0.0, 50.0]$ | BESS charging power |
| `battery_discharge_kw`| float | kW | $[0.0, 50.0]$ | BESS discharging power |
| `fuel_consumption_l` | float | L | $[0.0, 60.0]$ | Hourly diesel fuel consumed |
| `temperature_c` | float | °C | $[-55.0, 15.0]$ | Ambient outdoor air temperature |
| `humidity_percent` | float | % | $[10.0, 100.0]$ | Relative humidity |
| `pressure_hpa` | float | hPa | $[920.0, 1040.0]$ | Barometric pressure |
| `wind_speed_mps` | float | m/s | $[0.0, 65.0]$ | Wind speed |
| `sensor_anomaly_score`| float | z-score | $[0.0, 500.0]$ | Upstream Sensor ML composite score |
| `sensor_anomaly_status`| string | Cat | `NORMAL`, `ANOMALY`, `MISSING_DATA` | Upstream Sensor ML operational status |
| `sensor_anomaly_type`| string | Cat | `NORMAL`, `SPIKE`, `DRIFT`, `STUCK_VALUE`, `None` | Upstream Sensor ML failure mode |
| `event_type` | string | Cat | `NORMAL`, `STORM`, `EXTREME_COLD`, `HIGH_LOAD`, `POWER_CONSTRAINT` | Operational scenario |
| `source` | string | Cat | `SYNTHETIC_POLARIX_OPERATIONAL` | Data provenance origin |
| `data_quality` | string | Cat | `GOOD`, `MISSING` | Telemetry acquisition quality |

### Forecasting Targets (Future Causal Lookahead):
- `target_power_demand_1h_kw`: $P_{\text{demand}}(t+1)$ (1-hour ahead load forecasting).
- `target_battery_soc_1h_percent`: $\text{SoC}(t+1)$ (1-hour ahead battery state).
- `target_energy_demand_6h_kwh`: $\sum_{k=1}^6 E_{\text{demand}}(t+k)$ (6-hour ahead energy demand for generator staging).
- `target_energy_demand_24h_kwh`: $\sum_{k=1}^{24} E_{\text{demand}}(t+k)$ (24-hour ahead day-ahead scheduling budget).
- `target_energy_deficit_risk`: Binary risk indicator ($1$ if $\text{SoC}(t+1) < 25\%$ or $P_{\text{demand}}(t+1) > 0.95 P_{\text{rated}}$, else $0$).

---

## 6. Strict Chronological Split & Leakage Prevention

To prevent data snooping and lookahead leakage in time-series forecasting, splits are strictly temporal:

| Partition | Share | Hours per Station | Timestamp Boundary (Maitri & Bharati) |
|:---|:---|:---|:---|
| **Train** | 70.0% | 6,132 hrs | `2026-01-01T00:00:00Z` $\rightarrow$ `2026-09-13T11:00:00Z` |
| **Validation**| 15.0% | 1,314 hrs | `2026-09-13T12:00:00Z` $\rightarrow$ `2026-11-07T05:00:00Z` |
| **Test** | 15.0% | 1,314 hrs | `2026-11-07T06:00:00Z` $\rightarrow$ `2026-12-31T23:00:00Z` |

### Causal Anti-Leakage Invariants:
1. **No Target Leakage in Features:** All input features at timestamp $t$ only contain data known at or before $t$.
2. **Scaler Hygiene:** Future scalers (MinMaxScaler / StandardScaler) must be fit **exclusively** on the Train partition ($t \le \text{2026-09-13T11:00:00Z}$).
3. **Causal Rolling Statistics:** Any rolling window feature (e.g. 6-hour moving average) is backward-looking ($[t-W, t]$), never centered or forward-looking.
4. **Boundary Tail Handling:** Targets at the series boundary ($t > N - H$) are strictly `NaN` and dropped during sequence preparation.

---

## 7. Artifact Manifest & Verification Hashes

The generated dataset files and authoritative SHA-256 digests are:

- `maitri_energy_telemetry.csv` (8,760 rows): `9a40b28e11f004f0ce3b4ffa97f90aef3fa8a754cb32d56739918ae7b86ecb0e`
- `bharati_energy_telemetry.csv` (8,760 rows): `e2a9d4d3bcfe5400621cfcb3222a64e0e58ae9e7daacc6a6a2fdd159a362c8b5`
- `polarix_energy_telemetry.csv` (17,520 rows): `5e5e0c754d8a6280af30cfe67394ab89fc1390fac703b7fe61d85b576019d003`
- `energy_dataset_manifest.json`: Machine-readable metadata specification.

---

## 8. Limitations & Future Scope

1. **Renewable Penetration:** The initial dataset focuses on diesel-BESS hybrid topology. Wind turbine and PV solar arrays will be integrated in secondary microgrid expansion steps.
2. **Degradation Effects:** Battery capacity degradation ($SOH$) is assumed constant over the 1-year timeline. Multi-year battery cycle aging models can be layered on in subsequent studies.
