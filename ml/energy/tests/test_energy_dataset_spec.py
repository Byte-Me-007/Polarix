"""
Unit and Contract Tests for Polarix Energy Dataset Specification & Provenance.

Validates:
1. Existence and valid JSON parsing of energy_dataset_spec.json.
2. Station scope definition strictly covering Maitri ('MTR') and Bharati ('BRT').
3. Canonical schema completeness (types, units, ranges, nullability).
4. Truth in data provenance (no synthetic energy field falsely labeled as real data).
5. Multi-horizon forecasting targets (1h, 6h, 24h, and deficit risk).
6. Temporal split integrity (70% train, 15% val, 15% test; strict chronological split).
7. Strict architectural isolation between Sensor ML and Energy ML.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest


@pytest.fixture
def spec_path() -> Path:
    """Return path to canonical energy dataset specification file."""
    p = Path("ml/energy/data/energy_dataset_spec.json")
    assert p.exists(), f"Energy dataset spec file not found at {p}"
    return p


@pytest.fixture
def spec_data(spec_path: Path) -> dict:
    """Load and parse energy dataset specification JSON."""
    with open(spec_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def test_1_spec_file_valid_structure(spec_data: dict) -> None:
    """1. Spec file has valid structure, metadata, and versioning."""
    assert spec_data["spec_version"] == "1.0.0"
    assert spec_data["module"] == "ml.energy"
    assert "station_scopes" in spec_data
    assert "canonical_fields" in spec_data
    assert "forecasting_targets" in spec_data
    assert "temporal_split_strategy" in spec_data
    assert "provenance_disclaimer" in spec_data


def test_2_station_scopes(spec_data: dict) -> None:
    """2. Station scopes are strictly 'MTR' (Maitri) and 'BRT' (Bharati)."""
    stations = spec_data["station_scopes"]
    assert set(stations) == {"MTR", "BRT"}

    meta = spec_data["station_metadata"]
    assert "MTR" in meta and meta["MTR"]["station_name"] == "Maitri"
    assert "BRT" in meta and meta["BRT"]["station_name"] == "Bharati"
    assert meta["MTR"]["nominal_generation_kw"] > 0
    assert meta["BRT"]["nominal_generation_kw"] > 0
    assert meta["MTR"]["bess_capacity_kwh"] > 0
    assert meta["BRT"]["bess_capacity_kwh"] > 0


def test_3_canonical_fields_completeness(spec_data: dict) -> None:
    """3. All required canonical microgrid and environmental fields are defined."""
    fields = spec_data["canonical_fields"]
    required_fields = [
        "timestamp",
        "station_id",
        "power_demand_kw",
        "generator_output_kw",
        "energy_consumption_kwh",
        "battery_soc_percent",
        "battery_charge_kw",
        "battery_discharge_kw",
        "fuel_consumption_l",
        "temperature_c",
        "humidity_percent",
        "pressure_hpa",
        "wind_speed_mps",
        "sensor_anomaly_score",
        "sensor_anomaly_status",
        "sensor_anomaly_type",
        "source",
        "data_quality",
    ]
    for rf in required_fields:
        assert rf in fields, f"Missing required canonical field: {rf}"
        f_info = fields[rf]
        assert "type" in f_info
        assert "provenance" in f_info
        assert "nullable" in f_info
        if f_info["type"] == "float" and "valid_range" in f_info:
            r = f_info["valid_range"]
            assert len(r) == 2 and r[0] < r[1]


def test_4_truth_in_data_provenance(spec_data: dict) -> None:
    """4. Synthetic fields are explicitly declared and not falsely claimed as real Maitri/Bharati energy telemetry."""
    fields = spec_data["canonical_fields"]

    # Power and battery operational fields must be classified as synthetic/derived
    assert fields["power_demand_kw"]["provenance"] == "SYNTHETIC_POLARIX_OPERATIONAL"
    assert fields["generator_output_kw"]["provenance"] == "SYNTHETIC_POLARIX_OPERATIONAL"
    assert fields["battery_soc_percent"]["provenance"] == "SYNTHETIC_POLARIX_OPERATIONAL"
    assert fields["energy_consumption_kwh"]["provenance"] == "DERIVED_METRIC"
    assert fields["fuel_consumption_l"]["provenance"] == "DERIVED_METRIC"

    # Weather fields are marked as bounded by real public Indian expedition archives
    assert fields["temperature_c"]["provenance"] == "REAL_PUBLIC_INDIAN_WEATHER_BOUNDED"
    assert fields["pressure_hpa"]["provenance"] == "REAL_PUBLIC_INDIAN_WEATHER_BOUNDED"
    assert fields["wind_speed_mps"]["provenance"] == "REAL_PUBLIC_INDIAN_WEATHER_BOUNDED"

    # Upstream Sensor ML features
    assert fields["sensor_anomaly_score"]["provenance"] == "UPSTREAM_SENSOR_ML_FEATURE"
    assert fields["sensor_anomaly_status"]["provenance"] == "UPSTREAM_SENSOR_ML_FEATURE"


def test_5_forecasting_targets_defined(spec_data: dict) -> None:
    """5. Multi-horizon targets are defined with appropriate units and physical horizon."""
    targets = spec_data["forecasting_targets"]
    assert "target_power_demand_1h_kw" in targets
    assert "target_battery_soc_1h_percent" in targets
    assert "target_energy_demand_6h_kwh" in targets
    assert "target_energy_demand_24h_kwh" in targets
    assert "target_energy_deficit_risk" in targets

    assert targets["target_power_demand_1h_kw"]["unit"] == "kW"
    assert targets["target_battery_soc_1h_percent"]["unit"] == "%"
    assert targets["target_energy_demand_6h_kwh"]["unit"] == "kWh"
    assert targets["target_energy_demand_24h_kwh"]["unit"] == "kWh"
    assert targets["target_energy_deficit_risk"]["target_type"] == "classification"


def test_6_temporal_split_leakage_rules(spec_data: dict) -> None:
    """6. Temporal split is strictly chronological and sums to 1.0 (70/15/15)."""
    split = spec_data["temporal_split_strategy"]
    tr = split["train_ratio"]
    vr = split["val_ratio"]
    te = split["test_ratio"]
    assert abs((tr + vr + te) - 1.0) < 1e-6
    assert tr == 0.70
    assert vr == 0.15
    assert te == 0.15
    assert len(split["leakage_prevention_rules"]) >= 4


def test_7_sensor_ml_subsystem_isolation() -> None:
    """7. Sensor ML models and scripts remain intact outside ml/energy/."""
    assert Path("ml/models/lstm-ae-v1.pt").exists()
    assert Path("ml/models/lstm-ae-bharati-v1.pt").exists()
    assert Path("ml/inference/maitri_ml_service.py").exists()
    assert Path("ml/inference/bharati_ml_service.py").exists()
    # Confirm Sensor ML models are strictly isolated from ml/energy/models/
    assert not Path("ml/energy/models/lstm-ae-v1.pt").exists(), "Sensor ML Maitri model must not be inside energy models directory."
    assert not Path("ml/energy/models/lstm-ae-bharati-v1.pt").exists(), "Sensor ML Bharati model must not be inside energy models directory."
