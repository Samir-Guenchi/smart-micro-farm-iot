import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import HistGradientBoostingRegressor

from soil_drying.features import FEATURES, HORIZON_H, build_dataset, feature_row, hours_to_threshold
from soil_drying.policies import POLICIES, compare
from soil_drying.predict import SoilDryingModel
from soil_drying.simulate import Bed, make_beds, make_weather, step

BED = Bed("b", field_capacity=38, wilting_point=12, root_depth_mm=300, crop_factor=1.0)


def test_simulation_is_deterministic():
    a = make_weather(np.random.default_rng(3), 10)
    b = make_weather(np.random.default_rng(3), 10)
    assert np.array_equal(a.rain_mm, b.rain_mm) and len(a.temp_c) == 240


def test_water_balance_dries_and_rewets():
    assert step(30, BED, 0, 0, 0.5) < 30  # evapotranspiration dries the soil
    assert step(30, BED, 0, 10, 0) > 30  # irrigation wets it
    assert step(37.9, BED, 30, 0, 0) <= 38 + 30 / 300 * 100  # drainage above field capacity


def test_hours_to_threshold_is_capped_and_faster_when_drier():
    w = make_weather(np.random.default_rng(1), 10)
    w.rain_mm[:] = 0
    assert hours_to_threshold(26, BED, w, 0) < hours_to_threshold(32, BED, w, 0) <= HORIZON_H


def test_feature_row_has_every_feature_and_sees_rewetting():
    hist = np.r_[np.linspace(30, 25, 20), np.linspace(29, 28.5, 5)]  # watered 5 hours ago
    row = feature_row(hist, 20, 60, 18, 0, 4)
    assert list(row) == FEATURES
    assert row["hours_since_rewet"] == 4 and row["drying_rate"] < 0


@pytest.fixture(scope="module")
def tiny_model():
    rng = np.random.default_rng(0)
    df = build_dataset(rng, make_beds(rng, 2), make_weather(rng, 40))
    model = HistGradientBoostingRegressor(max_iter=50, random_state=0).fit(df[FEATURES], df.target_h)
    return model, df


def test_dataset_targets_in_range(tiny_model):
    _, df = tiny_model
    assert df.target_h.between(1, HORIZON_H).all() and set(FEATURES) <= set(df.columns)


def test_policies_run_and_sensor_watering_beats_habit(tiny_model):
    model, _ = tiny_model
    rng = np.random.default_rng(2)
    predict = lambda row: float(model.predict(pd.DataFrame([row], columns=FEATURES))[0])
    r = compare(make_beds(rng, 2), make_weather(rng, 40), seed=1, predict=predict).groupby("policy").liters.sum()
    assert set(r.index) == set(POLICIES)
    assert r["threshold"] < r["schedule"] and r["model"] < r["schedule"]


def test_exported_model_loads_and_rain_delays_watering():
    m = SoilDryingModel.load()
    assert m.meta["features"] == FEATURES
    history = np.linspace(31, 27, 25)
    dry = m.predict(history, 26, 50, 18, forecast_rain_24h=0, forecast_et0_24h=5)
    wet = m.predict(history, 18, 85, 18, forecast_rain_24h=12, forecast_et0_24h=2)
    assert 0 <= dry < wet <= HORIZON_H
    with pytest.raises(ValueError):
        m.predict(history[:10], 20, 60, 12, 0, 4)
