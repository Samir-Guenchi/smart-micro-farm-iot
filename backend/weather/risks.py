"""Weather risks for the next days: heat wave, sirocco (hot dry wind), frost, strong wind.

Pure functions over an Open-Meteo hourly forecast (timeformat=unixtime), so they can be tested
without the network. weather.py publishes each new risk once per farm-local day as an event on
greenloop/weather/event, where ingest stores it and the alert bot turns it into a Telegram message.

Thresholds are environment variables (see README.md). The defaults suit North Africa and
southern Europe; a farmer in a cooler climate can lower HEAT_C.
"""

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

HOURLY_VARS = "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_gusts_10m"


@dataclass
class RiskConfig:
    heat_c: float = 38.0  # max temperature that counts as a heat day
    sirocco_c: float = 35.0  # hot, dry, windy in the same hour
    sirocco_humidity_pct: float = 20.0
    sirocco_wind_kmh: float = 30.0
    frost_c: float = 2.0  # air at 2 m; ground frost starts a few degrees above 0
    gust_kmh: float = 60.0
    window_h: int = 48

    @classmethod
    def from_env(cls):
        d = cls()
        env = os.environ.get
        return cls(
            heat_c=float(env("HEAT_C", d.heat_c)),
            sirocco_c=float(env("SIROCCO_C", d.sirocco_c)),
            sirocco_humidity_pct=float(env("SIROCCO_HUMIDITY_PCT", d.sirocco_humidity_pct)),
            sirocco_wind_kmh=float(env("SIROCCO_WIND_KMH", d.sirocco_wind_kmh)),
            frost_c=float(env("FROST_C", d.frost_c)),
            gust_kmh=float(env("GUST_KMH", d.gust_kmh)),
            window_h=int(env("RISK_WINDOW_H", d.window_h)),
        )


@dataclass
class Risk:
    kind: str  # heat | sirocco | frost | wind
    day: str  # farm-local date of the first risky hour, YYYY-MM-DD
    start: int  # first risky hour (unix)
    peak_ts: int  # hour of the worst value (unix)
    peak: float  # °C for heat/frost/sirocco, km/h for wind
    hours: int  # number of risky hours in the window that day

    def event(self):
        """Payload for greenloop/weather/event."""
        return {"type": "weather_risk", "state": self.kind, **{k: v for k, v in asdict(self).items() if k != "kind"}}


def _day(ts, offset_s):
    return datetime.fromtimestamp(ts + offset_s, timezone.utc).strftime("%Y-%m-%d")


def detect(forecast, now, cfg: RiskConfig):
    """Risks in the next cfg.window_h hours, at most one per kind per farm-local day, in time order."""
    hourly = forecast["hourly"]
    times = hourly["time"]
    n = len(times)
    temp = hourly.get("temperature_2m") or [None] * n
    rh = hourly.get("relative_humidity_2m") or [None] * n
    wind = hourly.get("wind_speed_10m") or [None] * n
    gust = hourly.get("wind_gusts_10m") or [None] * n
    offset = int(forecast.get("utc_offset_seconds") or 0)
    end = now + cfg.window_h * 3600

    found = {}  # (kind, day) -> Risk

    def hit(kind, ts, value, worse):
        key = (kind, _day(ts, offset))
        risk = found.get(key)
        if risk is None:
            found[key] = Risk(kind, key[1], int(ts), int(ts), round(float(value), 1), 1)
            return
        risk.hours += 1
        if worse(value, risk.peak):
            risk.peak, risk.peak_ts = round(float(value), 1), int(ts)

    higher = lambda a, b: a > b  # noqa: E731
    lower = lambda a, b: a < b  # noqa: E731
    for i, ts in enumerate(times):
        if ts + 3600 <= now or ts >= end:
            continue
        t, h, w, g = temp[i], rh[i], wind[i], gust[i]
        if t is not None and t >= cfg.heat_c:
            hit("heat", ts, t, higher)
        if t is not None and t <= cfg.frost_c:
            hit("frost", ts, t, lower)
        if None not in (t, h, w) and t >= cfg.sirocco_c and h <= cfg.sirocco_humidity_pct and w >= cfg.sirocco_wind_kmh:
            hit("sirocco", ts, t, higher)
        if g is not None and g >= cfg.gust_kmh:
            hit("wind", ts, g, higher)
    return sorted(found.values(), key=lambda r: (r.start, r.kind))


class Notified:
    """Remembers which (kind, day) risks were already published, so a 3-hourly check doesn't repeat them."""

    def __init__(self):
        self.sent = set()

    def new(self, risks):
        out = [r for r in risks if (r.kind, r.day) not in self.sent]
        self.sent.update((r.kind, r.day) for r in out)
        # Forget days that are long gone so the set stays small.
        if len(self.sent) > 200:
            self.sent = set(sorted(self.sent, key=lambda k: k[1])[-100:])
        return out
