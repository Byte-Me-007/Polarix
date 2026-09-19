"""
Tests for Environmental Baselines (Polarix SIH26060 - Person C).
"""

import numpy as np
import pandas as pd
import pytest

from ml.environmental.training.baselines import PersistenceForecaster, RecentMeanForecaster


def test_persistence_forecaster():
    forecaster = PersistenceForecaster()
    df = pd.DataFrame({
        "wind_speed_mps": [10.0, 15.0],
        "pressure_hpa": [980.0, 975.0],
        "humidity_percent": [60.0, 65.0],
    })
    res = forecaster.predict_window(df)

    assert res["wind_speed_mps"]["1h"] == 15.0
    assert res["pressure_hpa"]["6h"] == 975.0
    assert res["humidity_percent"]["24h"] == 65.0

    arr = forecaster.predict_dataframe(df)
    assert arr.shape == (2, 9)
    # Check wind persistence (first 3 cols)
    np.testing.assert_array_equal(arr[:, 0], np.array([10.0, 15.0]))


def test_recent_mean_forecaster():
    forecaster = RecentMeanForecaster(window_size=2)
    df = pd.DataFrame({
        "wind_speed_mps": [10.0, 20.0],
        "pressure_hpa": [980.0, 1000.0],
        "humidity_percent": [50.0, 70.0],
    })
    res = forecaster.predict_window(df)

    assert res["wind_speed_mps"]["1h"] == 15.0
    assert res["pressure_hpa"]["6h"] == 990.0
    assert res["humidity_percent"]["24h"] == 60.0

    arr = forecaster.predict_dataframe(df)
    assert arr.shape == (2, 9)
    assert pytest.approx(arr[1, 0], rel=1e-3) == 15.0


def test_empty_baseline_input():
    forecaster = PersistenceForecaster()
    with pytest.raises(ValueError, match="cannot be empty"):
        forecaster.predict_window(pd.DataFrame())
