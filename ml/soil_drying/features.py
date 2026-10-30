"""Turn readings into model features and (for training) the target.

Features use only what the farm will really have at prediction time: the soil
moisture history from the sensor, the current temperature and humidity, and
the forecast. The target is the number of hours until moisture falls below the
threshold *if nobody waters*, capped at HORIZON_H.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .simulate import Bed, Weather, forecast_24h, step

HORIZON_H = 72
THRESHOLD = 25.0
FEATURES = [
    "moisture",
    "moisture_above_threshold",
    "slope_6h",
    "slope_24h",
    "drying_rate",
    "hours_since_rewet",
    "air_temp_c",
    "air_humidity_pct",
    "hour_sin",
    "hour_cos",
    "forecast_rain_24h",
    "forecast_et0_24h",
]


def feature_row(history: np.ndarray, temp: float, humidity: float, hour: int, fc_rain: float, fc_et0: float,
                threshold: float = THRESHOLD) -> dict:
    """Features from the last >=25 hourly moisture readings (oldest first) and the current conditions."""
    history = np.asarray(history, dtype=float)
    m = float(history[-3:].mean())  # average the last 3 readings to damp sensor noise
    # Watering or rain shows as a jump up; the drying rate is only meaningful after the last jump.
    jumps = np.where(np.diff(history) > 2.0)[0]
    since = len(history) - 1 - (int(jumps[-1]) + 1) if len(jumps) else len(history) - 1
    seg = history[-(since + 1):] if since >= 3 else history[-4:]
    rate = float(np.polyfit(np.arange(len(seg)), seg, 1)[0])  # %/h, negative while drying
    return {
        "moisture": m,
        "moisture_above_threshold": m - threshold,
        "slope_6h": (m - float(history[-7])) / 6,
        "slope_24h": (m - float(history[-25])) / 24,
        "drying_rate": rate,
        "hours_since_rewet": since,
        "air_temp_c": temp,
        "air_humidity_pct": humidity,
        "hour_sin": float(np.sin(2 * np.pi * hour / 24)),
        "hour_cos": float(np.cos(2 * np.pi * hour / 24)),
        "forecast_rain_24h": fc_rain,
        "forecast_et0_24h": fc_et0,
    }


def hours_to_threshold(theta: float, bed: Bed, weather: Weather, t: int, threshold: float = THRESHOLD) -> int:
    """Roll the bed forward with no irrigation and count hours until moisture < threshold."""
    for h in range(HORIZON_H):
        if t + h >= len(weather.rain_mm):
            return HORIZON_H
        theta = step(theta, bed, weather.rain_mm[t + h], 0.0, weather.et0_mm[t + h])
        if theta < threshold:
            return h + 1
    return HORIZON_H


def build_dataset(rng: np.random.Generator, beds: list[Bed], weather: Weather, every_h: int = 3,
                  sensor_noise: float = 0.4) -> pd.DataFrame:
    """Simulate each bed, sampling features and targets as it goes.

    Each bed is watered with its own random trigger level (18-32%) and dose
    (8-25 mm), so the data covers wet and dry soil, not only the narrow band a
    single threshold rule would keep it in.
    """
    rows = []
    n = len(weather.rain_mm)
    for bed in beds:
        trigger = float(rng.uniform(18, 32))
        dose = float(rng.uniform(8, 25))
        theta = bed.field_capacity
        hist = []
        last_water = -999
        for t in range(n - HORIZON_H):
            reading = theta + rng.normal(0, sensor_noise)
            hist.append(reading)
            if t >= 25 and t % every_h == 0:
                fc_rain, fc_et0 = forecast_24h(rng, weather, t)
                row = feature_row(np.array(hist[-25:]), weather.temp_c[t], weather.humidity_pct[t], t % 24, fc_rain, fc_et0)
                row["target_h"] = hours_to_threshold(theta, bed, weather, t)
                row["bed"] = bed.name
                row["t"] = t
                rows.append(row)
            irrigation = 0.0
            if reading < trigger and t - last_water >= 6:
                irrigation, last_water = dose, t
            theta = step(theta, bed, weather.rain_mm[t], irrigation, weather.et0_mm[t])
    return pd.DataFrame(rows)
