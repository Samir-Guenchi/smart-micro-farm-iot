"""Sunrise and sunset times from coordinates, with no external dependencies.

Uses the sunrise equation (https://en.wikipedia.org/wiki/Sunrise_equation),
accurate to a minute or two, which is plenty for a "door still open after
sunset" alert.
"""

import math
from datetime import date, datetime, timedelta, timezone


def sun_times(day: date, lat: float, lon: float):
    """Returns (sunrise, sunset) as aware UTC datetimes, or (None, None) during polar day/night."""
    # Days since J2000.0 at local noon.
    n = (datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc) - datetime(2000, 1, 1, 12, tzinfo=timezone.utc)).days
    mean_solar_noon = n - lon / 360
    m = math.radians((357.5291 + 0.98560028 * mean_solar_noon) % 360)
    center = 1.9148 * math.sin(m) + 0.02 * math.sin(2 * m) + 0.0003 * math.sin(3 * m)
    ecliptic_lon = math.radians((math.degrees(m) + center + 180 + 102.9372) % 360)
    transit = 2451545.0 + mean_solar_noon + 0.0053 * math.sin(m) - 0.0069 * math.sin(2 * ecliptic_lon)
    declination = math.asin(math.sin(ecliptic_lon) * math.sin(math.radians(23.4397)))
    phi = math.radians(lat)
    cos_h = (math.sin(math.radians(-0.833)) - math.sin(phi) * math.sin(declination)) / (math.cos(phi) * math.cos(declination))
    if not -1 <= cos_h <= 1:
        return None, None
    h = math.degrees(math.acos(cos_h)) / 360

    def to_dt(julian):
        return datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=julian - 2451545.0)

    return to_dt(transit - h), to_dt(transit + h)
