"""Compare watering policies on simulated beds: liters used and hours the crop spent stressed."""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from .features import THRESHOLD, feature_row
from .simulate import Bed, Weather, forecast_24h, step

DOSE_MM = 10.0  # one 10-minute run: about 40 L on a 4 m2 bed
STRESS_MARGIN = 5.0  # below threshold - 5 the crop is stressed; every policy waters there
MIN_GAP_H = 6
CHECK_HOUR = 18  # evening: less evaporation, and the farmer can approve after work


def run(policy: str, bed: Bed, weather: Weather, rng: np.random.Generator,
        predict: Callable[[dict], float] | None = None, sensor_noise: float = 0.4) -> dict:
    """Simulate one bed under a policy.

    schedule            water every evening at CHECK_HOUR whatever the soil says (watering by habit)
    threshold           water when the reading is below the threshold (what the firmware does)
    threshold+forecast  same, but skip while >= 5 mm of rain is forecast in 24 h (the backend weather rule)
    model               once a day at CHECK_HOUR (like the agent's daily check), water if the model
                        predicts the bed will cross the threshold before the next check
    """
    theta = bed.field_capacity
    hist: list[float] = []
    last_water = -999
    liters = 0.0
    runs = 0
    stressed = 0
    below = 0
    for t in range(len(weather.rain_mm)):
        reading = theta + rng.normal(0, sensor_noise)
        hist.append(reading)
        fc_rain, fc_et0 = forecast_24h(rng, weather, t)
        can_water = t - last_water >= MIN_GAP_H
        guard = reading < THRESHOLD - STRESS_MARGIN
        if policy == "schedule":
            water = t % 24 == CHECK_HOUR or guard
        elif policy == "threshold":
            water = reading < THRESHOLD
        elif policy == "threshold+forecast":
            water = reading < THRESHOLD and (fc_rain < 5 or guard)
        elif policy == "model":
            water = guard
            if not water and t % 24 == CHECK_HOUR and len(hist) >= 25:
                row = feature_row(np.array(hist[-25:]), weather.temp_c[t], weather.humidity_pct[t], t % 24, fc_rain, fc_et0)
                water = predict(row) < 24
        else:
            raise ValueError(policy)
        irrigation = 0.0
        if water and can_water:
            irrigation, last_water = DOSE_MM, t
            liters += DOSE_MM * bed.area_m2
            runs += 1
        theta = step(theta, bed, weather.rain_mm[t], irrigation, weather.et0_mm[t])
        below += theta < THRESHOLD
        stressed += theta < THRESHOLD - STRESS_MARGIN
    return {"policy": policy, "bed": bed.name, "liters": liters, "runs": runs, "hours_below_threshold": below, "hours_stressed": stressed}


POLICIES = ["schedule", "threshold", "threshold+forecast", "model"]


def compare(beds: list[Bed], weather: Weather, seed: int, predict: Callable[[dict], float]) -> pd.DataFrame:
    rows = []
    for policy in POLICIES:
        rng = np.random.default_rng(seed)  # same sensor noise and forecasts for every policy
        rows += [run(policy, bed, weather, rng, predict) for bed in beds]
    return pd.DataFrame(rows)
