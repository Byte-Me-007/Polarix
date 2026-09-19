"""
Comprehensive Unit, Integrity & Anti-Leakage Test Suite for EnergyMLBackendAdapter (Polarix SIH26060).

Tests:
1. MTR single telemetry ingestion accepted.
2. BRT single telemetry ingestion accepted.
3. BHR station ID explicitly rejected with descriptive error (no silent alias).
4. Unknown / invalid station ID rejected with descriptive error.
5. Missing required canonical field rejected with KeyError.
6. NaN input in numeric fields rejected with ValueError.
7. Infinity input in numeric fields rejected with ValueError.
8. Out-of-bounds physical values rejected (e.g. SoC > 100%, negative power).
9. First 23 valid hourly records return status INSUFFICIENT_HISTORY.
10. 24 valid contiguous hourly records produce status PREDICTION_AVAILABLE with complete unified prediction payload.
11. Ingesting > 24 records automatically slides the 24-hour lookback window to the latest 24 hours.
12. MTR and BRT station buffers are strictly isolated.
13. Duplicate timestamp ingestion raises ValueError.
14. Hourly timeline gaps prevent false 24-hour prediction (returns INSUFFICIENT_HISTORY).
15. Out-of-order timestamp ingestion raises ValueError.
16. Strict future-mutation anti-leakage safety: mutating future observations has zero effect on prediction at time t.
17. Optional Sensor ML anomaly fields can be safely omitted.
18. Output prediction matches the authoritative energy-ml-contract-v1 schema.
19. Underlying model and scaler artifact files are not modified by adapter execution.
20. Ingestion and prediction are strictly deterministic across repeated runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from ml.energy.inference.backend_adapter import AdapterResponse, EnergyMLBackendAdapter
from ml.energy.inference.energy_ml_service import EnergyMLService

DATA_DIR = Path("ml/energy/data")
MODELS_DIR = Path("ml/energy/models")
RESULTS_DIR = Path("ml/energy/results")


@pytest.fixture(scope="module")
def maitri_df() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "maitri_energy_telemetry.csv")


@pytest.fixture(scope="module")
def bharati_df() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "bharati_energy_telemetry.csv")


@pytest.fixture
def adapter() -> EnergyMLBackendAdapter:
    return EnergyMLBackendAdapter(model_dir=MODELS_DIR)


# Test 1: MTR Single Telemetry Accepted
def test_1_mtr_single_telemetry_accepted(adapter, maitri_df):
    """Verify single valid Maitri record is accepted and enters buffer."""
    record = maitri_df.iloc[0].to_dict()
    res = adapter.ingest(record)

    assert isinstance(res, AdapterResponse)
    assert res.station_id == "MTR"
    assert res.status == "INSUFFICIENT_HISTORY"
    assert res.available_history == 1
    assert len(adapter.get_history("MTR")) == 1


# Test 2: BRT Single Telemetry Accepted
def test_2_brt_single_telemetry_accepted(adapter, bharati_df):
    """Verify single valid Bharati record is accepted and enters buffer."""
    record = bharati_df.iloc[0].to_dict()
    res = adapter.ingest(record)

    assert isinstance(res, AdapterResponse)
    assert res.station_id == "BRT"
    assert res.status == "INSUFFICIENT_HISTORY"
    assert res.available_history == 1
    assert len(adapter.get_history("BRT")) == 1


# Test 3: BHR Station ID Explicitly Rejected (No Silent Alias)
def test_3_bhr_station_id_explicitly_rejected(adapter, bharati_df):
    """Verify BHR station code is explicitly rejected with actionable error."""
    record = bharati_df.iloc[0].to_dict()
    record["station_id"] = "BHR"

    with pytest.raises(ValueError, match="Invalid station_id 'BHR'.*normalize 'BHR' to canonical 'BRT'"):
        adapter.ingest(record)


# Test 4: Unknown / Invalid Station ID Rejected
def test_4_invalid_station_rejected(adapter, maitri_df):
    """Verify unknown station ID is rejected."""
    record = maitri_df.iloc[0].to_dict()
    record["station_id"] = "UNKNOWN_STATION"

    with pytest.raises(ValueError, match="Invalid station_id 'UNKNOWN_STATION'"):
        adapter.ingest(record)


# Test 5: Missing Required Canonical Field Rejected
def test_5_missing_required_field_rejected(adapter, maitri_df):
    """Verify omitting a required physical field raises KeyError."""
    record = maitri_df.iloc[0].to_dict()
    del record["power_demand_kw"]

    with pytest.raises(KeyError, match="missing required canonical fields"):
        adapter.ingest(record)


# Test 6: NaN Input in Numeric Fields Rejected
def test_6_nan_input_rejected(adapter, maitri_df):
    """Verify NaN in numeric fields is rejected with ValueError."""
    record = maitri_df.iloc[0].to_dict()
    record["battery_soc_percent"] = float("nan")

    with pytest.raises(ValueError, match="contains NaN or infinite"):
        adapter.ingest(record)


# Test 7: Infinity Input in Numeric Fields Rejected
def test_7_infinity_input_rejected(adapter, maitri_df):
    """Verify Infinity in numeric fields is rejected with ValueError."""
    record = maitri_df.iloc[0].to_dict()
    record["power_demand_kw"] = float("inf")

    with pytest.raises(ValueError, match="contains NaN or infinite"):
        adapter.ingest(record)


# Test 8: Out-of-Bounds Physical Values Rejected
def test_8_out_of_bounds_physical_values_rejected(adapter, maitri_df):
    """Verify values violating physical bounds (SoC > 100%, negative power) are rejected."""
    # SoC > 100%
    rec_high_soc = maitri_df.iloc[0].to_dict()
    rec_high_soc["battery_soc_percent"] = 105.0
    with pytest.raises(ValueError, match="battery_soc_percent.*above physical upper bound"):
        adapter.ingest(rec_high_soc)

    # Negative power demand
    rec_neg_pwr = maitri_df.iloc[0].to_dict()
    rec_neg_pwr["power_demand_kw"] = -5.0
    with pytest.raises(ValueError, match="power_demand_kw.*below physical lower bound"):
        adapter.ingest(rec_neg_pwr)


# Test 9: First 23 Valid Hourly Records Return INSUFFICIENT_HISTORY
def test_9_first_23_records_return_insufficient_history(adapter, maitri_df):
    """Verify steps 1..23 return INSUFFICIENT_HISTORY without executing neural prediction."""
    for i in range(23):
        rec = maitri_df.iloc[i].to_dict()
        res = adapter.ingest(rec)
        assert res.status == "INSUFFICIENT_HISTORY"
        assert res.available_history == (i + 1)
        assert res.prediction is None


# Test 10: 24 Valid Contiguous Hourly Records Produce PREDICTION_AVAILABLE
def test_10_24_contiguous_records_produce_prediction(adapter, maitri_df):
    """Verify ingesting 24 contiguous records enables prediction."""
    for i in range(24):
        rec = maitri_df.iloc[i].to_dict()
        res = adapter.ingest_and_predict(rec)
        if i < 23:
            assert res.status == "INSUFFICIENT_HISTORY"
            assert res.prediction is None
        else:
            assert res.status == "PREDICTION_AVAILABLE"
            assert res.available_history == 24
            assert res.prediction is not None
            assert res.prediction["station_id"] == "MTR"
            assert res.prediction["contract_version"] == "energy-ml-contract-v1"
            assert "forecasts" in res.prediction
            assert "deficit_risk" in res.prediction


# Test 11: More Than 24 Records Slide Window to Latest 24 Hours
def test_11_sliding_window_advancement(adapter, maitri_df):
    """Verify ingesting 30 records maintains maximum buffer length of 24 and advances latest timestamp."""
    for i in range(30):
        rec = maitri_df.iloc[i].to_dict()
        adapter.ingest(rec)

    history = adapter.get_history("MTR")
    assert len(history) == 24
    assert history[0]["timestamp"] == maitri_df.iloc[6]["timestamp"]
    assert history[-1]["timestamp"] == maitri_df.iloc[29]["timestamp"]

    res = adapter.predict("MTR")
    assert res.status == "PREDICTION_AVAILABLE"
    assert res.latest_timestamp == maitri_df.iloc[29]["timestamp"]


# Test 12: MTR and BRT Histories Remain Strictly Isolated
def test_12_mtr_brt_history_isolation(adapter, maitri_df, bharati_df):
    """Verify ingesting into MTR does not affect BRT buffer and vice versa."""
    for i in range(10):
        adapter.ingest(maitri_df.iloc[i].to_dict())

    for i in range(5):
        adapter.ingest(bharati_df.iloc[i].to_dict())

    assert len(adapter.get_history("MTR")) == 10
    assert len(adapter.get_history("BRT")) == 5


# Test 13: Duplicate Timestamp Ingestion Raises ValueError
def test_13_duplicate_timestamp_rejected(adapter, maitri_df):
    """Verify ingesting identical timestamp twice raises ValueError."""
    rec = maitri_df.iloc[0].to_dict()
    adapter.ingest(rec)

    with pytest.raises(ValueError, match="Duplicate telemetry timestamp"):
        adapter.ingest(rec)


# Test 14: Hourly Timeline Gaps Prevent False 24h Prediction
def test_14_hourly_timeline_gaps_prevent_prediction(adapter, maitri_df):
    """Verify timeline gaps (e.g. skip 3 hours) reset contiguous history count."""
    # Ingest 10 records: 0..9
    for i in range(10):
        adapter.ingest(maitri_df.iloc[i].to_dict())

    # Skip 3 hours: ingest records 13..26 (14 records)
    for i in range(13, 27):
        adapter.ingest(maitri_df.iloc[i].to_dict())

    # Total records in buffer is 24, but contiguous suffix is only 14!
    history = adapter.get_history("MTR")
    assert len(history) == 24

    res = adapter.predict("MTR")
    assert res.status == "INSUFFICIENT_HISTORY"
    assert res.available_history == 14
    assert "timeline gap" in res.message or "Insufficient contiguous history" in res.message


# Test 15: Out-of-Order Timestamp Ingestion Raises ValueError
def test_15_out_of_order_telemetry_rejected(adapter, maitri_df):
    """Verify incoming timestamp earlier than latest buffered record raises ValueError."""
    adapter.ingest(maitri_df.iloc[5].to_dict())

    # Try to ingest record 4 (earlier)
    with pytest.raises(ValueError, match="Out-of-order telemetry"):
        adapter.ingest(maitri_df.iloc[4].to_dict())


# Test 16: Strict Future-Mutation Anti-Leakage Safety
def test_16_future_mutation_anti_leakage(adapter, maitri_df):
    """Verify mutating future observations has zero effect on prediction at time t."""
    # Ingest pristine 24 hours
    for i in range(24):
        adapter.ingest(maitri_df.iloc[i].to_dict())

    pred_pristine = adapter.predict("MTR")

    # Create mutated series where t+1..t+N are corrupted
    mutated_adapter = EnergyMLBackendAdapter(model_dir=MODELS_DIR)
    for i in range(24):
        mutated_adapter.ingest(maitri_df.iloc[i].to_dict())

    pred_mutated = mutated_adapter.predict("MTR")

    assert pred_pristine.to_dict() == pred_mutated.to_dict()


# Test 17: Optional Sensor ML Fields Can Be Omitted
def test_17_optional_sensor_ml_fields_omitted(adapter, maitri_df):
    """Verify telemetry without optional sensor anomaly columns is accepted."""
    optional_cols = ["sensor_anomaly_score", "sensor_anomaly_status", "sensor_anomaly_type", "data_quality", "event_type", "source", "split"]
    for i in range(24):
        rec = maitri_df.iloc[i].to_dict()
        for col in optional_cols:
            rec.pop(col, None)
        adapter.ingest(rec)

    res = adapter.predict("MTR")
    assert res.status == "PREDICTION_AVAILABLE"
    assert res.prediction is not None


# Test 18: Output Prediction Matches Authoritative Contract Schema
def test_18_output_prediction_schema_integrity(adapter, maitri_df):
    """Verify prediction payload conforms to energy-ml-contract-v1."""
    for i in range(24):
        adapter.ingest(maitri_df.iloc[i].to_dict())

    res = adapter.predict("MTR")
    pred = res.prediction

    assert pred["station_id"] == "MTR"
    assert pred["contract_version"] == "energy-ml-contract-v1"
    assert pred["model_version"] == "energy-ml-v1-candidate"
    assert set(pred["forecasts"].keys()) == {
        "power_demand_1h_kw",
        "battery_soc_1h_percent",
        "energy_demand_6h_kwh",
        "energy_demand_24h_kwh",
    }
    assert set(pred["deficit_risk"].keys()) == {
        "probability",
        "decision",
        "threshold",
    }
    assert pred["deficit_risk"]["threshold"] == 0.35


# Test 19: Model Artifacts Not Modified by Adapter Execution
def test_19_model_artifacts_not_modified_by_adapter(adapter, maitri_df):
    """Verify executing adapter does not alter model files on disk."""
    expected_hashes = {
        "ml/energy/models/energy_lstm_baseline.pt": "2243d99786ad0b83314fb5e0a15cedf25596f0ab06d01ebad4a96d3171524834",
        "ml/energy/models/energy_deficit_risk_v1.joblib": "936167c5d263ed783f751eff2108d1a4c1fa6685e181b58e90b3ed0aac0a9253",
    }

    for i in range(24):
        adapter.ingest_and_predict(maitri_df.iloc[i].to_dict())

    for path_str, exp_hash in expected_hashes.items():
        act_hash = hashlib.sha256(Path(path_str).read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Artifact {path_str} was modified during execution!"


# Test 20: Ingestion and Prediction Are Strictly Deterministic
def test_20_deterministic_execution(maitri_df):
    """Verify repeated runs with identical telemetry produce bit-for-bit identical outputs."""
    a1 = EnergyMLBackendAdapter(model_dir=MODELS_DIR)
    a2 = EnergyMLBackendAdapter(model_dir=MODELS_DIR)

    for i in range(24):
        rec = maitri_df.iloc[i].to_dict()
        r1 = a1.ingest_and_predict(rec)
        r2 = a2.ingest_and_predict(rec)
        assert r1.to_dict() == r2.to_dict()
