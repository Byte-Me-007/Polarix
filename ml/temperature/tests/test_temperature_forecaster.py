"""
Tests for Standalone TemperatureForecaster Inference Module (Polarix SIH26060 - Person C).
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.temperature.inference.temperature_forecaster import TemperatureForecaster


@pytest.fixture
def forecaster():
    return TemperatureForecaster()


@pytest.fixture
def valid_telemetry_mtr():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    df = pd.read_csv(data_dir / "maitri_temperature_telemetry.csv")
    return df.iloc[:24].copy().reset_index(drop=True)


@pytest.fixture
def valid_telemetry_brt():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    df = pd.read_csv(data_dir / "bharati_temperature_telemetry.csv")
    return df.iloc[:24].copy().reset_index(drop=True)


def test_forecaster_initialization(forecaster):
    assert forecaster.model_version == "temperature-lstm-v1"
    assert forecaster.lookback == 24
    assert forecaster.model is not None
    assert forecaster.scaler is not None


def test_predict_window_mtr_valid(forecaster, valid_telemetry_mtr):
    res = forecaster.predict_window("MTR", valid_telemetry_mtr)

    assert res["status"] == "PREDICTION_AVAILABLE"
    assert res["station_id"] == "MTR"
    assert res["model_version"] == "temperature-lstm-v1"
    assert "forecasts" in res and res["forecasts"] is not None

    forecasts = res["forecasts"]
    for horizon in ["temperature_1h_c", "temperature_6h_c", "temperature_24h_c"]:
        assert horizon in forecasts
        val = forecasts[horizon]
        assert isinstance(val, float)
        assert not np.isnan(val)
        assert not np.isinf(val)
        assert -60.0 <= val <= 30.0  # reasonable physical bounds

    assert res["provenance"]["source"] == "SYNTHETIC_POLARIX_DATA"
    assert res["provenance"]["model_status"] == "CANDIDATE"


def test_predict_window_brt_valid(forecaster, valid_telemetry_brt):
    res = forecaster.predict_window("BRT", valid_telemetry_brt)

    assert res["status"] == "PREDICTION_AVAILABLE"
    assert res["station_id"] == "BRT"
    assert "forecasts" in res and res["forecasts"] is not None
    assert isinstance(res["forecasts"]["temperature_1h_c"], float)


def test_predict_dict(forecaster, valid_telemetry_mtr):
    records = valid_telemetry_mtr.to_dict(orient="records")
    res = forecaster.predict_dict("MTR", records)

    assert res["status"] == "PREDICTION_AVAILABLE"
    assert res["station_id"] == "MTR"
    assert "forecasts" in res and res["forecasts"] is not None


def test_predict_dataframe(forecaster, valid_telemetry_mtr):
    # Pass a 30-hour dataframe
    data_dir = Path(__file__).resolve().parent.parent / "data"
    df = pd.read_csv(data_dir / "maitri_temperature_telemetry.csv").iloc[:30].copy()
    res_df = forecaster.predict_dataframe(df)

    assert "pred_temperature_1h_c" in res_df.columns
    assert "pred_temperature_6h_c" in res_df.columns
    assert "pred_temperature_24h_c" in res_df.columns

    # First 23 rows should be NaN due to lookback=24 requirement
    assert res_df["pred_temperature_1h_c"].iloc[:23].isna().all()
    # From index 23 onwards, predictions should be finite floats
    assert not res_df["pred_temperature_1h_c"].iloc[23:].isna().any()


def test_invalid_station_id(forecaster, valid_telemetry_mtr):
    res = forecaster.predict_window("UNKNOWN_STATION", valid_telemetry_mtr)
    assert res["status"] == "INVALID_INPUT"
    assert "Invalid station_id" in res["error_detail"]
    assert res["forecasts"] is None


def test_insufficient_history(forecaster, valid_telemetry_mtr):
    short_df = valid_telemetry_mtr.iloc[:10].copy()
    res = forecaster.predict_window("MTR", short_df)
    assert res["status"] == "INSUFFICIENT_HISTORY"
    assert "INSUFFICIENT_HISTORY" in res["error_detail"]
    assert res["forecasts"] is None


def test_nan_telemetry_rejection(forecaster, valid_telemetry_mtr):
    bad_df = valid_telemetry_mtr.copy()
    bad_df.loc[5, "temperature_c"] = np.nan
    res = forecaster.predict_window("MTR", bad_df)
    assert res["status"] == "INVALID_INPUT"
    assert "NaN" in res["error_detail"]


def test_inf_telemetry_rejection(forecaster, valid_telemetry_mtr):
    bad_df = valid_telemetry_mtr.copy()
    bad_df.loc[5, "wind_speed_mps"] = np.inf
    res = forecaster.predict_window("MTR", bad_df)
    assert res["status"] == "INVALID_INPUT"
    assert "Inf" in res["error_detail"]


def test_duplicate_timestamp_rejection(forecaster, valid_telemetry_mtr):
    bad_df = valid_telemetry_mtr.copy()
    bad_df.loc[5, "timestamp"] = bad_df.loc[4, "timestamp"]
    res = forecaster.predict_window("MTR", bad_df)
    assert res["status"] == "INVALID_INPUT"
    assert "duplicate" in res["error_detail"].lower()


def test_irregular_time_gaps_rejection(forecaster, valid_telemetry_mtr):
    bad_df = valid_telemetry_mtr.copy()
    # Create a 5-hour gap between row 10 and 11
    bad_df.loc[11:, "timestamp"] = pd.date_range(
        start="2026-01-02T10:00:00Z", periods=len(bad_df) - 11, freq="h", tz="UTC"
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    res = forecaster.predict_window("MTR", bad_df)
    assert res["status"] == "INVALID_INPUT"
    assert "gap" in res["error_detail"].lower()


def test_missing_required_columns(forecaster, valid_telemetry_mtr):
    bad_df = valid_telemetry_mtr.drop(columns=["pressure_hpa"])
    res = forecaster.predict_window("MTR", bad_df)
    assert res["status"] == "INVALID_INPUT"
    assert "Missing required telemetry columns" in res["error_detail"]
