"""Simulated beds and weather, so the model can be built before the farm has a season of data.

A daily-cycle weather generator drives a simple root-zone water balance per bed:

    d(theta) = (rain + irrigation - Kc * ET0 * stress(theta) - drainage) / root_depth

theta is volumetric soil moisture in %, like the irrigation node's soil_moisture_pct.
Each bed gets its own soil (field capacity, wilting point, depth) and crop factor,
which the model never sees: it has to infer them from how fast the reading falls.
Replace this with real data once a season exists; nothing else in the package
depends on how the readings were produced.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

HOURS_PER_DAY = 24


@dataclass
class Bed:
    name: str
    field_capacity: float  # % moisture after drainage
    wilting_point: float  # % moisture where plants can no longer draw water
    root_depth_mm: float
    crop_factor: float  # Kc
    area_m2: float = 4.0


@dataclass
class Weather:
    temp_c: np.ndarray  # hourly
    humidity_pct: np.ndarray
    rain_mm: np.ndarray
    et0_mm: np.ndarray  # hourly reference evapotranspiration


def make_beds(rng: np.random.Generator, n: int) -> list[Bed]:
    return [
        Bed(
            name=f"bed-{i + 1}",
            field_capacity=float(rng.uniform(32, 42)),
            wilting_point=float(rng.uniform(10, 15)),
            root_depth_mm=float(rng.uniform(250, 400)),
            crop_factor=float(rng.uniform(0.8, 1.15)),
        )
        for i in range(n)
    ]


def make_weather(rng: np.random.Generator, days: int, climate: str = "temperate") -> Weather:
    """Hourly weather for a growing season. 'temperate' is roughly a Baltic summer, 'mediterranean' a dry North African spring."""
    hot = climate == "mediterranean"
    n = days * HOURS_PER_DAY
    hour = np.arange(n) % HOURS_PER_DAY
    day = np.arange(n) // HOURS_PER_DAY
    season = np.sin(np.pi * day / max(days - 1, 1))  # warmest mid-season
    tmax = (24 if hot else 17) + (8 if hot else 7) * season + np.repeat(rng.normal(0, 2.5, days), HOURS_PER_DAY)
    tmin = tmax - rng.uniform(8, 12)
    daily_cycle = np.sin((hour - 9) / 24 * 2 * np.pi)
    temp = (tmax + tmin) / 2 + (tmax - tmin) / 2 * daily_cycle
    humidity = np.clip((45 if hot else 70) - 18 * daily_cycle + rng.normal(0, 4, n), 15, 100)

    rain = np.zeros(n)
    rain_prob = 0.12 if hot else 0.32
    for d in range(days):
        if rng.random() < rain_prob:
            start = d * HOURS_PER_DAY + rng.integers(0, 24)
            length = int(rng.integers(1, 7))
            total = rng.exponential(4 if hot else 6)
            rain[start : start + length] += total / length
    rain = rain[:n]
    humidity = np.where(rain > 0, np.maximum(humidity, 90), humidity)

    # Hargreaves-like ET0, shaped over daylight hours and damped by humidity and rain.
    daylight = np.clip(np.sin((hour - 5) / 15 * np.pi), 0, None)
    daily_et0 = 0.0023 * 1.0 * (temp + 17.8) * np.sqrt(np.maximum(tmax - tmin, 1)) * 30
    et0 = daily_et0 * daylight / daylight[:24].sum() * (1.2 - humidity / 200)
    et0 = np.where(rain > 0, et0 * 0.3, et0)
    return Weather(temp, humidity, rain, np.maximum(et0, 0))


def step(theta: float, bed: Bed, rain_mm: float, irrigation_mm: float, et0_mm: float) -> float:
    """Advance one hour of the water balance. Returns the new moisture in %."""
    stress = np.clip((theta - bed.wilting_point) / (0.6 * (bed.field_capacity - bed.wilting_point)), 0, 1)
    et = bed.crop_factor * et0_mm * stress
    theta = theta + (0.85 * rain_mm + irrigation_mm - et) / bed.root_depth_mm * 100
    if theta > bed.field_capacity:  # excess drains away over a few hours
        theta -= 0.35 * (theta - bed.field_capacity)
    return float(np.clip(theta, bed.wilting_point - 2, 50))


def forecast_24h(rng: np.random.Generator, weather: Weather, t: int, hours: int = 24) -> tuple[float, float]:
    """A noisy forecast of rain and ET0 over the next `hours`, like a weather API would give.

    Rain is missed 15% of the time and occasionally predicted when none falls.
    """
    true_rain = float(weather.rain_mm[t : t + hours].sum())
    true_et0 = float(weather.et0_mm[t : t + hours].sum())
    if true_rain > 0:
        fc_rain = 0.0 if rng.random() < 0.15 else true_rain * float(rng.lognormal(0, 0.5))
    else:
        fc_rain = float(rng.exponential(4)) if rng.random() < 0.08 else 0.0
    return fc_rain, true_et0 * float(rng.normal(1, 0.1))


def liters_to_mm(liters: float, bed: Bed) -> float:
    return liters / bed.area_m2
