"""
Tests for Temperature Dataset Specification (Polarix SIH26060 - Person C).
"""

import json
from pathlib import Path
import pytest


def test_temperature_dataset_spec_structure():
    spec_path = Path(__file__).resolve().parent.parent / "data" / "temperature_dataset_spec.json"
    assert spec_path.exists(), f"Spec file not found at {spec_path}"

    with open(spec_path, "r") as f:
        spec = json.load(f)

    assert spec["spec_version"] == "1.0.0"
    assert "MTR" in spec["station_scopes"]
    assert "BRT" in spec["station_scopes"]
    assert "SYNTHETIC_POLARIX_DATA" in spec["provenance_disclaimer"]

    # Check station metadata
    assert "MTR" in spec["station_metadata"]
    assert "BRT" in spec["station_metadata"]
    assert spec["station_metadata"]["MTR"]["station_name"] == "Maitri"
    assert spec["station_metadata"]["BRT"]["station_name"] == "Bharati"

    # Check canonical features
    feature_names = [f["name"] for f in spec["canonical_features"]]
    for req in ["timestamp", "station_id", "temperature_c", "humidity_percent", "pressure_hpa", "wind_speed_mps"]:
        assert req in feature_names

    # Check forecasting targets
    target_names = [t["name"] for t in spec["forecasting_targets"]]
    assert "target_temperature_1h_c" in target_names
    assert "target_temperature_6h_c" in target_names
    assert "target_temperature_24h_c" in target_names

    # Check split ratios
    split = spec["temporal_split_strategy"]
    assert split["train_ratio"] == 0.70
    assert split["val_ratio"] == 0.15
    assert split["test_ratio"] == 0.15
    assert split["total_records_per_station"] == 8760
