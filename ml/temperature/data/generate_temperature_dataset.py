"""
Deterministic Synthetic Temperature ML Dataset Generator (Polarix SIH26060 - Person C).

Generates physically grounded, high-fidelity synthetic meteorological telemetry
for Indian Antarctic Research Stations:
- Maitri ('MTR'): Inland Antarctic rock oasis (Schirmacher Oasis, 70.77°S, 11.73°E, elevation 117m).
- Bharati ('BRT'): Coastal promontory (Larsemann Hills, 69.40°S, 76.18°E, elevation 35m).

Calibrated against empirical bounds from NCPOR & AADC public meteorological archives.
Dataset is explicitly tagged as SYNTHETIC_POLARIX_DATA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TemperatureDatasetGenerator")


@dataclass(frozen=True)
class StationClimateProfile:
    """Climatic and geographic parameters for Antarctic meteorological simulation."""
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    elevation_m: float
    mean_temp_c: float
    annual_temp_amplitude_c: float
    diurnal_temp_amplitude_c: float
    min_temp_c: float
    max_temp_c: float
    mean_pressure_hpa: float
    pressure_std_hpa: float
    mean_humidity_pct: float
    humidity_std_pct: float
    mean_wind_mps: float
    blizzard_probability: float


STATION_PROFILES: Dict[str, StationClimateProfile] = {
    "MTR": StationClimateProfile(
        station_id="MTR",
        station_name="Maitri",
        latitude=-70.7667,
        longitude=11.7333,
        elevation_m=117.0,
        mean_temp_c=-10.5,
        annual_temp_amplitude_c=16.5,  # Winter lows ~ -35C to -40C, Summer highs ~ +5C
        diurnal_temp_amplitude_c=4.5,
        min_temp_c=-45.0,
        max_temp_c=8.0,
        mean_pressure_hpa=985.0,
        pressure_std_hpa=12.0,
        mean_humidity_pct=60.0,
        humidity_std_pct=14.0,
        mean_wind_mps=9.5,
        blizzard_probability=0.06,
    ),
    "BRT": StationClimateProfile(
        station_id="BRT",
        station_name="Bharati",
        latitude=-69.4000,
        longitude=76.1833,
        elevation_m=35.0,
        mean_temp_c=-8.5,
        annual_temp_amplitude_c=14.0,  # Winter lows ~ -30C to -35C, Summer highs ~ +8C
        diurnal_temp_amplitude_c=3.5,
        min_temp_c=-38.0,
        max_temp_c=10.0,
        mean_pressure_hpa=993.0,
        pressure_std_hpa=15.0,
        mean_humidity_pct=72.0,
        humidity_std_pct=16.0,
        mean_wind_mps=11.0,
        blizzard_probability=0.09,
    ),
}


def compute_solar_elevation_rad(latitude_deg: float, day_of_year: int, hour_utc: float, longitude_deg: float) -> float:
    """Computes approximate solar elevation angle in radians for polar solar geometry."""
    # Solar declination angle delta
    declination = 23.45 * math.sin(math.radians((360.0 / 365.0) * (day_of_year - 81)))
    declination_rad = math.radians(declination)
    lat_rad = math.radians(latitude_deg)

    # Local solar time
    solar_time_hours = (hour_utc + (longitude_deg / 15.0)) % 24.0
    hour_angle_deg = 15.0 * (solar_time_hours - 12.0)
    hour_angle_rad = math.radians(hour_angle_deg)

    sin_elevation = math.sin(lat_rad) * math.sin(declination_rad) + math.cos(lat_rad) * math.cos(declination_rad) * math.cos(hour_angle_rad)
    return math.asin(max(-1.0, min(1.0, sin_elevation)))


def simulate_station_series(
    profile: StationClimateProfile,
    start_date: str = "2026-01-01T00:00:00Z",
    total_hours: int = 8760,
    seed: int = 42,
) -> pd.DataFrame:
    """Simulates a continuous 8,760-hour hourly meteorological time-series for an Antarctic station."""
    rng = np.random.RandomState(seed)
    timestamps = pd.date_range(start=start_date, periods=total_hours, freq="h", tz="UTC")

    # Time indicators
    hours = np.array([ts.hour for ts in timestamps])
    days_of_year = np.array([ts.dayofyear for ts in timestamps])
    sin_hour = np.sin(2.0 * np.pi * hours / 24.0)
    cos_hour = np.cos(2.0 * np.pi * hours / 24.0)
    sin_day = np.sin(2.0 * np.pi * days_of_year / 365.25)
    cos_day = np.cos(2.0 * np.pi * days_of_year / 365.25)

    # 1. Base Annual Seasonal Cycle (Southern Hemisphere: Summer in Dec/Jan/Feb, Winter in June/July/Aug)
    # Peak summer occurs near day 15 (mid January), deep winter occurs near day 198 (mid July)
    phase_shift_annual = 15.0
    seasonal_cycle = profile.mean_temp_c + profile.annual_temp_amplitude_c * np.cos(
        2.0 * np.pi * (days_of_year - phase_shift_annual) / 365.25
    )

    # 2. Solar Elevation and Diurnal Variation
    solar_elevations = np.array([
        compute_solar_elevation_rad(profile.latitude, day, hr, profile.longitude)
        for day, hr in zip(days_of_year, hours)
    ])
    # Diurnal solar heating is active when sun is above or near horizon
    diurnal_effect = profile.diurnal_temp_amplitude_c * np.sin(np.maximum(0.0, solar_elevations))

    # 3. Barometric Synoptic Waves (Synoptic weather fronts pass every 3-7 days = 72-168 hours)
    synoptic_phase_1 = rng.uniform(0, 2 * np.pi)
    synoptic_phase_2 = rng.uniform(0, 2 * np.pi)
    t_idx = np.arange(total_hours)

    synoptic_pressure_wave = (
        12.0 * np.sin(2.0 * np.pi * t_idx / 120.0 + synoptic_phase_1)
        + 6.0 * np.cos(2.0 * np.pi * t_idx / 64.0 + synoptic_phase_2)
    )

    # AR(1) process for pressure weather perturbations
    ar_pressure = np.zeros(total_hours)
    phi_p = 0.95
    for i in range(1, total_hours):
        ar_pressure[i] = phi_p * ar_pressure[i - 1] + rng.normal(0.0, 1.8)

    pressure_hpa = profile.mean_pressure_hpa + synoptic_pressure_wave + ar_pressure
    pressure_hpa = np.clip(pressure_hpa, 915.0, 1040.0)

    # 4. Wind Speed and Katabatic / Storm Surges
    # Strong low pressure systems (cyclones) bring high winds and warmer marine air
    pressure_anomaly = (pressure_hpa - profile.mean_pressure_hpa) / profile.pressure_std_hpa
    base_wind = profile.mean_wind_mps - 4.0 * pressure_anomaly  # Deep low pressure -> high wind

    # Katabatic nocturnal drain flow in winter
    katabatic_surge = np.where(solar_elevations < 0.0, 3.5 * np.abs(np.sin(2.0 * np.pi * hours / 24.0)), 0.0)
    
    # Random blizzard events (persistent high wind multi-hour clusters)
    blizzard_event = np.zeros(total_hours)
    i = 0
    while i < total_hours:
        if rng.uniform(0.0, 1.0) < (profile.blizzard_probability / 48.0):
            duration = rng.randint(12, 60)
            end_idx = min(total_hours, i + duration)
            surge_strength = rng.uniform(15.0, 32.0)
            blizzard_event[i:end_idx] = surge_strength
            i = end_idx
        else:
            i += 1

    wind_speed_mps = base_wind + katabatic_surge + blizzard_event + rng.normal(0.0, 2.0, size=total_hours)
    wind_speed_mps = np.clip(wind_speed_mps, 0.2, 62.0)

    # 5. Humidity
    # In Antarctica, low pressure marine advection brings higher humidity; high wind/snow also increases RH
    rh_anomaly = -12.0 * pressure_anomaly + 0.3 * wind_speed_mps
    humidity_percent = profile.mean_humidity_pct + rh_anomaly + rng.normal(0.0, 5.0, size=total_hours)
    humidity_percent = np.clip(humidity_percent, 15.0, 99.0)

    # 6. Temperature Synthesis
    # Low pressure synoptic storms bring warm maritime air into the continent (foehn / advection warming)
    storm_warming = np.where(pressure_anomaly < -1.0, -4.5 * pressure_anomaly, 0.0)
    # Wind mixing prevents nocturnal radiation inversion cooling (inversion breakdown warming)
    inversion_mixing = np.where(wind_speed_mps > 15.0, 2.5 * (wind_speed_mps - 15.0) / 10.0, 0.0)

    # Autoregressive thermal inertia AR(1)
    thermal_noise = np.zeros(total_hours)
    phi_t = 0.94
    for i in range(1, total_hours):
        thermal_noise[i] = phi_t * thermal_noise[i - 1] + rng.normal(0.0, 0.75)

    temperature_c = seasonal_cycle + diurnal_effect + storm_warming + inversion_mixing + thermal_noise
    temperature_c = np.clip(temperature_c, profile.min_temp_c, profile.max_temp_c)

    # Construct DataFrame
    df = pd.DataFrame({
        "timestamp": [ts.strftime("%Y-%m-%dT%H:%M:%SZ") for ts in timestamps],
        "station_id": profile.station_id,
        "temperature_c": np.round(temperature_c, 2),
        "humidity_percent": np.round(humidity_percent, 1),
        "pressure_hpa": np.round(pressure_hpa, 1),
        "wind_speed_mps": np.round(wind_speed_mps, 2),
        "hour": hours,
        "day_of_year": days_of_year,
        "sin_hour": np.round(sin_hour, 5),
        "cos_hour": np.round(cos_hour, 5),
        "sin_day": np.round(sin_day, 5),
        "cos_day": np.round(cos_day, 5),
    })

    # Causal Multi-Horizon Targets
    # target_temperature_1h_c: temp at t + 1 hour
    # target_temperature_6h_c: temp at t + 6 hours
    # target_temperature_24h_c: temp at t + 24 hours
    df["target_temperature_1h_c"] = df["temperature_c"].shift(-1)
    df["target_temperature_6h_c"] = df["temperature_c"].shift(-6)
    df["target_temperature_24h_c"] = df["temperature_c"].shift(-24)

    return df


def calculate_sha256(filepath: Path) -> str:
    """Calculates SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_all_datasets(output_dir: Path, seed: int = 42) -> Dict[str, Any]:
    """Generates MTR, BRT, and Combined telemetry datasets and writes metadata manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Generating deterministic synthetic datasets in {output_dir} with seed={seed}")

    df_mtr = simulate_station_series(STATION_PROFILES["MTR"], seed=seed)
    df_brt = simulate_station_series(STATION_PROFILES["BRT"], seed=seed + 100)

    mtr_path = output_dir / "maitri_temperature_telemetry.csv"
    brt_path = output_dir / "bharati_temperature_telemetry.csv"
    combined_path = output_dir / "polarix_temperature_telemetry.csv"

    df_mtr.to_csv(mtr_path, index=False)
    df_brt.to_csv(brt_path, index=False)

    # Interleave / concatenate in station-grouped or chronological order
    df_combined = pd.concat([df_mtr, df_brt], ignore_index=True)
    df_combined.to_csv(combined_path, index=False)

    # Hashes and manifest
    manifest = {
        "manifest_version": "1.0.0",
        "subsystem": "Temperature Forecasting ML Subsystem",
        "data_provenance": "SYNTHETIC_POLARIX_DATA",
        "provenance_disclaimer": "Generated deterministically from physically grounded Antarctic meteorological transfer equations and seasonal solar geometry conditioned on NCPOR empirical bounds.",
        "random_seed": seed,
        "stations": {
            "MTR": {
                "records": len(df_mtr),
                "filename": "maitri_temperature_telemetry.csv",
                "sha256": calculate_sha256(mtr_path),
                "temp_stats": {
                    "mean": float(df_mtr["temperature_c"].mean()),
                    "min": float(df_mtr["temperature_c"].min()),
                    "max": float(df_mtr["temperature_c"].max()),
                    "std": float(df_mtr["temperature_c"].std()),
                }
            },
            "BRT": {
                "records": len(df_brt),
                "filename": "bharati_temperature_telemetry.csv",
                "sha256": calculate_sha256(brt_path),
                "temp_stats": {
                    "mean": float(df_brt["temperature_c"].mean()),
                    "min": float(df_brt["temperature_c"].min()),
                    "max": float(df_brt["temperature_c"].max()),
                    "std": float(df_brt["temperature_c"].std()),
                }
            },
            "COMBINED": {
                "records": len(df_combined),
                "filename": "polarix_temperature_telemetry.csv",
                "sha256": calculate_sha256(combined_path),
            }
        },
        "chronological_splits": {
            "train_period": "2026-01-01T00:00:00Z to 2026-09-13T17:00:00Z (6,132 records / station)",
            "val_period": "2026-09-13T18:00:00Z to 2026-11-07T05:00:00Z (1,314 records / station)",
            "test_period": "2026-11-07T06:00:00Z to 2026-12-31T23:00:00Z (1,314 records / station)"
        }
    }

    manifest_path = output_dir / "temperature_dataset_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Dataset generation complete. Manifest saved at {manifest_path}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Polarix Temperature ML Datasets")
    parser.add_argument("--output-dir", type=str, default=str(Path(__file__).parent), help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    generate_all_datasets(Path(args.output_dir), seed=args.seed)
