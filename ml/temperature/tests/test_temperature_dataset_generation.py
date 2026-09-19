"""
Tests for Temperature Dataset Generation (Polarix SIH26060 - Person C).
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.temperature.data.generate_temperature_dataset import (
    STATION_PROFILES,
    simulate_station_series,
)


def test_simulate_station_series_deterministic():
    df1 = simulate_station_series(STATION_PROFILES["MTR"], total_hours=48, seed=42)
    df2 = simulate_station_series(STATION_PROFILES["MTR"], total_hours=48, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_generated_dataset_files():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    mtr_path = data_dir / "maitri_temperature_telemetry.csv"
    brt_path = data_dir / "bharati_temperature_telemetry.csv"
    comb_path = data_dir / "polarix_temperature_telemetry.csv"

    assert mtr_path.exists()
    assert brt_path.exists()
    assert comb_path.exists()

    df_mtr = pd.read_csv(mtr_path)
    df_brt = pd.read_csv(brt_path)
    df_comb = pd.read_csv(comb_path)

    assert len(df_mtr) == 8760
    assert len(df_brt) == 8760
    assert len(df_comb) == 17520

    for df, st_id in [(df_mtr, "MTR"), (df_brt, "BRT")]:
        assert (df["station_id"] == st_id).all()
        # Non-null check on telemetry columns
        for col in ["temperature_c", "humidity_percent", "pressure_hpa", "wind_speed_mps"]:
            assert not df[col].isna().any()
            assert not np.isinf(df[col]).any()

        # Check physical bounds
        assert (df["humidity_percent"] >= 10.0).all() and (df["humidity_percent"] <= 100.0).all()
        assert (df["pressure_hpa"] >= 900.0).all() and (df["pressure_hpa"] <= 1050.0).all()
        assert (df["wind_speed_mps"] >= 0.0).all() and (df["wind_speed_mps"] <= 65.0).all()

        # Check target alignment
        # target_temperature_1h_c at t should equal temperature_c at t+1
        assert df["target_temperature_1h_c"].iloc[0] == df["temperature_c"].iloc[1]
        assert df["target_temperature_6h_c"].iloc[0] == df["temperature_c"].iloc[6]
        assert df["target_temperature_24h_c"].iloc[0] == df["temperature_c"].iloc[24]
