"""
Tests for Environmental Dataset Generation (Polarix SIH26060 - Person C).
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.environmental.data.generate_environmental_dataset import (
    STATION_PROFILES,
    simulate_environmental_series,
)


def test_simulate_environmental_series_deterministic():
    df1 = simulate_environmental_series(STATION_PROFILES["MTR"], total_hours=48, seed=42)
    df2 = simulate_environmental_series(STATION_PROFILES["MTR"], total_hours=48, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_generated_dataset_files():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    mtr_path = data_dir / "maitri_environmental_telemetry.csv"
    brt_path = data_dir / "bharati_environmental_telemetry.csv"
    comb_path = data_dir / "polarix_environmental_telemetry.csv"

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

        for col in ["wind_speed_mps", "pressure_hpa", "humidity_percent", "temperature_c"]:
            assert not df[col].isna().any()
            assert not np.isinf(df[col]).any()

        # Check physical bounds
        assert (df["wind_speed_mps"] >= 0.0).all() and (df["wind_speed_mps"] <= 65.0).all()
        assert (df["pressure_hpa"] >= 900.0).all() and (df["pressure_hpa"] <= 1050.0).all()
        assert (df["humidity_percent"] >= 10.0).all() and (df["humidity_percent"] <= 100.0).all()

        # Check forward shift alignment for all 3 variables
        assert df["target_wind_speed_1h_mps"].iloc[0] == df["wind_speed_mps"].iloc[1]
        assert df["target_wind_speed_6h_mps"].iloc[0] == df["wind_speed_mps"].iloc[6]
        assert df["target_wind_speed_24h_mps"].iloc[0] == df["wind_speed_mps"].iloc[24]

        assert df["target_pressure_1h_hpa"].iloc[0] == df["pressure_hpa"].iloc[1]
        assert df["target_pressure_6h_hpa"].iloc[0] == df["pressure_hpa"].iloc[6]
        assert df["target_pressure_24h_hpa"].iloc[0] == df["pressure_hpa"].iloc[24]

        assert df["target_humidity_1h_percent"].iloc[0] == df["humidity_percent"].iloc[1]
        assert df["target_humidity_6h_percent"].iloc[0] == df["humidity_percent"].iloc[6]
        assert df["target_humidity_24h_percent"].iloc[0] == df["humidity_percent"].iloc[24]
