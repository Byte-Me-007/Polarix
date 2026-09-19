"""
Causal Feature Engineering for Energy Deficit-Risk Prediction (Polarix SIH26060).

Extracts strictly contemporaneous and backward-looking historical features:
- Core microgrid telemetry (power, generator, battery, fuel)
- Correlated weather features (temperature, humidity, pressure, wind)
- Upstream Sensor ML anomaly features (score, status, quality)
- Cyclical temporal features (sin/cos hour and day of year)
- Domain microgrid indicators (utilization, battery net flow, thermal headroom, rolling slopes)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

RISK_FEATURE_COLUMNS: List[str] = [
    "power_demand_kw",
    "generator_output_kw",
    "battery_soc_percent",
    "battery_charge_kw",
    "battery_discharge_kw",
    "fuel_consumption_l",
    "temperature_c",
    "humidity_percent",
    "pressure_hpa",
    "wind_speed_mps",
    "sensor_anomaly_score",
    "sensor_is_anomaly",
    "sensor_is_missing",
    "station_is_brt",
    "sin_hour",
    "cos_hour",
    "sin_day",
    "cos_day",
    "generator_utilization",
    "demand_to_gen_ratio",
    "battery_net_power",
    "recent_demand_mean_6h",
    "recent_demand_slope_3h",
    "recent_soc_mean_6h",
    "recent_soc_slope_3h",
    "thermal_headroom",
]

REQUIRED_RAW_COLUMNS: List[str] = [
    "timestamp",
    "station_id",
    "power_demand_kw",
    "generator_output_kw",
    "battery_soc_percent",
    "battery_charge_kw",
    "battery_discharge_kw",
    "fuel_consumption_l",
    "temperature_c",
    "humidity_percent",
    "pressure_hpa",
    "wind_speed_mps",
]

PHYSICAL_BOUNDS: dict[str, tuple[float | None, float | None]] = {
    "battery_soc_percent": (0.0, 100.0),
    "humidity_percent": (0.0, 100.0),
    "pressure_hpa": (850.0, 1100.0),
    "temperature_c": (-65.0, 25.0),
    "wind_speed_mps": (0.0, 80.0),
    "power_demand_kw": (0.0, 300.0),
    "generator_output_kw": (0.0, 300.0),
    "battery_charge_kw": (0.0, 100.0),
    "battery_discharge_kw": (0.0, 100.0),
    "fuel_consumption_l": (0.0, 100.0),
}

TARGET_COLUMN: str = "target_energy_deficit_risk"

TARGET_COLUMNS_EXCLUDED: List[str] = [
    "target_power_demand_1h_kw",
    "target_battery_soc_1h_percent",
    "target_energy_demand_6h_kwh",
    "target_energy_demand_24h_kwh",
    "target_energy_deficit_risk",
]


def validate_risk_telemetry(df: pd.DataFrame) -> None:
    """
    Validate input telemetry DataFrame against schema and physical invariants.
    Raises ValueError or KeyError with descriptive diagnostic messages if malformed.
    """
    if len(df) == 0:
        raise ValueError("Input telemetry DataFrame is empty.")

    missing_cols = [c for c in REQUIRED_RAW_COLUMNS if c not in df.columns]
    if missing_cols:
        raise KeyError(f"Input telemetry missing required columns: {missing_cols}")

    # Check station_id validity
    invalid_stations = set(df["station_id"].unique()) - {"MTR", "BRT"}
    if invalid_stations:
        raise ValueError(f"Invalid station_id encountered: {invalid_stations}. Expected 'MTR' or 'BRT'.")

    # Check for NaN / Inf in required numeric columns
    numeric_cols = [
        "power_demand_kw",
        "generator_output_kw",
        "battery_soc_percent",
        "battery_charge_kw",
        "battery_discharge_kw",
        "fuel_consumption_l",
        "temperature_c",
        "humidity_percent",
        "pressure_hpa",
        "wind_speed_mps",
    ]
    for col in numeric_cols:
        vals = pd.to_numeric(df[col], errors="coerce").to_numpy()
        if np.any(np.isnan(vals)) or np.any(np.isinf(vals)):
            raise ValueError(f"Column '{col}' contains NaN or infinite values.")

    # Check physical bounds
    for col, (low, high) in PHYSICAL_BOUNDS.items():
        if col in df.columns:
            vals = df[col].to_numpy(dtype=float)
            if low is not None and np.any(vals < low):
                min_val = float(np.min(vals))
                raise ValueError(f"Column '{col}' has value {min_val:.3f} below physical lower bound {low}.")
            if high is not None and np.any(vals > high):
                max_val = float(np.max(vals))
                raise ValueError(f"Column '{col}' has value {max_val:.3f} above physical upper bound {high}.")


def extract_risk_features(df: pd.DataFrame, validate: bool = True) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Extract strictly causal feature set and binary target series from station telemetry.

    Guarantees:
    - Input validation on physical bounds and required fields.
    - No lookahead leakage: all rolling features and slopes use values at or before timestamp t.
    - Deterministic, causal, and self-contained.
    - Future targets are strictly excluded from the extracted feature DataFrame.
    """
    if validate:
        validate_risk_telemetry(df)
    df_out = df.copy()

    # Parse timestamps for cyclical temporal embeddings
    ts = pd.to_datetime(df_out["timestamp"], utc=True)
    hour = ts.dt.hour.to_numpy()
    dayofyear = ts.dt.dayofyear.to_numpy()

    df_out["sin_hour"] = np.sin(2.0 * np.pi * hour / 24.0)
    df_out["cos_hour"] = np.cos(2.0 * np.pi * hour / 24.0)
    df_out["sin_day"] = np.sin(2.0 * np.pi * dayofyear / 365.25)
    df_out["cos_day"] = np.cos(2.0 * np.pi * dayofyear / 365.25)

    # Station encoding: 0.0 for MTR, 1.0 for BRT
    is_brt = (df_out["station_id"] == "BRT").astype(float)
    df_out["station_is_brt"] = is_brt

    # Station generator rated power (120 kW MTR, 150 kW BRT)
    rated_gen = np.where(is_brt == 1.0, 150.0, 120.0)
    df_out["generator_utilization"] = np.clip(df_out["generator_output_kw"] / rated_gen, 0.0, 2.0)
    df_out["demand_to_gen_ratio"] = np.clip(
        df_out["power_demand_kw"] / (df_out["generator_output_kw"] + 1e-4), 0.0, 5.0
    )
    df_out["battery_net_power"] = df_out["battery_charge_kw"] - df_out["battery_discharge_kw"]
    df_out["thermal_headroom"] = np.maximum(0.0, 18.0 - df_out["temperature_c"])

    # Sensor ML status encoding with safe optional defaulting
    sensor_status = (
        df_out["sensor_anomaly_status"]
        if "sensor_anomaly_status" in df_out.columns
        else pd.Series("NORMAL", index=df_out.index)
    )
    data_quality = (
        df_out["data_quality"]
        if "data_quality" in df_out.columns
        else pd.Series("GOOD", index=df_out.index)
    )
    sensor_score = (
        df_out["sensor_anomaly_score"]
        if "sensor_anomaly_score" in df_out.columns
        else pd.Series(1.0, index=df_out.index)
    )

    df_out["sensor_is_anomaly"] = (sensor_status == "ANOMALY").astype(float)
    df_out["sensor_is_missing"] = (
        (sensor_status == "MISSING_DATA") | (data_quality == "MISSING")
    ).astype(float)
    df_out["sensor_anomaly_score"] = sensor_score.fillna(1.0).astype(float)

    # Causal Rolling Features (backward-looking only)
    # 6-hour rolling mean of power demand
    df_out["recent_demand_mean_6h"] = (
        df_out["power_demand_kw"].rolling(window=6, min_periods=1).mean()
    )
    # 3-hour backward slope of power demand: (P(t) - P(t-3)) / 3.0
    p_shift_3 = df_out["power_demand_kw"].shift(3).fillna(df_out["power_demand_kw"])
    df_out["recent_demand_slope_3h"] = (df_out["power_demand_kw"] - p_shift_3) / 3.0

    # 6-hour rolling mean of battery SoC
    df_out["recent_soc_mean_6h"] = (
        df_out["battery_soc_percent"].rolling(window=6, min_periods=1).mean()
    )
    # 3-hour backward slope of battery SoC: (SoC(t) - SoC(t-3)) / 3.0
    soc_shift_3 = df_out["battery_soc_percent"].shift(3).fillna(df_out["battery_soc_percent"])
    df_out["recent_soc_slope_3h"] = (df_out["battery_soc_percent"] - soc_shift_3) / 3.0

    # Verify all required features exist
    for col in RISK_FEATURE_COLUMNS:
        if col not in df_out.columns:
            raise ValueError(f"Missing required risk feature column: {col}")

    X_df = df_out[RISK_FEATURE_COLUMNS].copy()
    y_series = df_out[TARGET_COLUMN].copy() if TARGET_COLUMN in df_out.columns else pd.Series(index=df.index, dtype=float)

    return X_df, y_series
