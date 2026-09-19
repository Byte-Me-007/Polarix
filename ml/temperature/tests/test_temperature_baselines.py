"""
Tests for Temperature Baselines (Polarix SIH26060 - Person C).
"""

import numpy as np
import pandas as pd
import pytest

from ml.temperature.training.baselines import PersistenceForecaster, RecentMeanForecaster


def test_persistence_forecaster():
    forecaster = PersistenceForecaster()
    temp_series = [-10.0, -12.0, -15.5]
    res = forecaster.predict_window(temp_series)

    assert res["temperature_1h_c"] == -15.5
    assert res["temperature_6h_c"] == -15.5
    assert res["temperature_24h_c"] == -15.5

    df = pd.DataFrame({"temperature_c": [1.0, 2.0, 3.0]})
    arr = forecaster.predict_dataframe(df)
    assert arr.shape == (3, 3)
    np.testing.assert_array_equal(arr[:, 0], np.array([1.0, 2.0, 3.0]))


def test_recent_mean_forecaster():
    forecaster = RecentMeanForecaster(window_size=3)
    temp_series = [10.0, 20.0, 30.0]
    res = forecaster.predict_window(temp_series)

    assert res["temperature_1h_c"] == 20.0
    assert res["temperature_6h_c"] == 20.0
    assert res["temperature_24h_c"] == 20.0

    df = pd.DataFrame({"temperature_c": [10.0, 20.0, 30.0, 40.0]})
    arr = forecaster.predict_dataframe(df)
    assert arr.shape == (4, 3)
    # rolling mean of size 3:
    # 0: 10.0
    # 1: 15.0
    # 2: 20.0
    # 3: (20+30+40)/3 = 30.0
    assert pytest.approx(arr[3, 0], rel=1e-3) == 30.0


def test_empty_baseline_input():
    forecaster = PersistenceForecaster()
    with pytest.raises(ValueError, match="Input series cannot be empty"):
        forecaster.predict_window([])
