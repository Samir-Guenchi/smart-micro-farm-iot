"""Weather-aware irrigation: skip automatic watering when rain is forecast.

Every few hours, reads the Open-Meteo forecast for the farm's coordinates.
If enough rain is likely in the next 24 h, publishes a retained
{"action": "skip_auto_water", "until": <unix ts>} to greenloop/irrigation-1/cmd.
Every decision is logged (JSON lines, and the database if DATABASE_URL is set)
so it can later be compared against water use.

Environment (see README.md):
  FARM_LATITUDE, FARM_LONGITUDE   farm coordinates
  RAIN_THRESHOLD_MM               skip if at least this much rain is forecast in the window (default 5)
  RAIN_MIN_PROBABILITY            ...and some hour in the window has at least this probability, % (default 60)
  FORECAST_WINDOW_H               look-ahead window in hours (default 24)
  CHECK_EVERY_H                   how often to check (default 3)
  IRRIGATION_NODE                 default irrigation-1
  MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD
  DECISION_LOG                    JSON lines file (default decisions.jsonl)
  DATABASE_URL                    optional; decisions also go to the irrigation_decisions table
"""

import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

log = logging.getLogger("weather")

OPEN_METEO = os.environ.get("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")


@dataclass
class Config:
    latitude: float
    longitude: float
    threshold_mm: float = 5.0
    min_probability: float = 60.0
    window_h: int = 24
    node: str = "irrigation-1"

    @classmethod
    def from_env(cls):
        return cls(
            latitude=float(os.environ["FARM_LATITUDE"]),
            longitude=float(os.environ["FARM_LONGITUDE"]),
            threshold_mm=float(os.environ.get("RAIN_THRESHOLD_MM", "5")),
            min_probability=float(os.environ.get("RAIN_MIN_PROBABILITY", "60")),
            window_h=int(os.environ.get("FORECAST_WINDOW_H", "24")),
            node=os.environ.get("IRRIGATION_NODE", "irrigation-1"),
        )


@dataclass
class Decision:
    ts: int  # when the decision was made
    skip: bool
    until: int  # end of the skip; equal to ts when not skipping
    rain_mm: float  # total forecast precipitation in the window
    max_probability: float  # highest hourly precipitation probability in the window, %
    last_rain_ts: int | None  # start of the last forecast hour with rain in the window
    reason: str


def fetch_forecast(cfg, timeout=20):
    params = urllib.parse.urlencode({
        "latitude": cfg.latitude,
        "longitude": cfg.longitude,
        "hourly": "precipitation,precipitation_probability",
        "forecast_days": 3,
        "timeformat": "unixtime",
        "timezone": "UTC",
    })
    with urllib.request.urlopen(f"{OPEN_METEO}?{params}", timeout=timeout) as resp:
        return json.load(resp)


def decide(forecast, now, cfg):
    """Pure decision from an Open-Meteo response (timeformat=unixtime)."""
    hourly = forecast["hourly"]
    times = hourly["time"]
    rain = hourly.get("precipitation") or [0] * len(times)
    prob = hourly.get("precipitation_probability") or [None] * len(times)
    end = now + cfg.window_h * 3600

    total, max_p, last_rain = 0.0, 0.0, None
    for ts, mm, p in zip(times, rain, prob):
        # Include the hour that is in progress now.
        if ts + 3600 <= now or ts >= end:
            continue
        mm = mm or 0.0
        total += mm
        if p is not None:
            max_p = max(max_p, float(p))
        if mm > 0:
            last_rain = ts

    has_probability = any(p is not None for p in prob)
    likely = max_p >= cfg.min_probability or not has_probability
    skip = total >= cfg.threshold_mm and likely
    if skip:
        # Skip until the window ends, or until 6 h after the last rainy hour if that is later
        # (soil stays wet after rain). Never more than 36 h, so one bad forecast can't dry a bed out.
        until = min(max(end, (last_rain or now) + 3600 + 6 * 3600), now + 36 * 3600)
        reason = f"{total:.1f} mm forecast in {cfg.window_h} h (max {max_p:.0f}% chance)"
    else:
        until = now
        if total < cfg.threshold_mm:
            reason = f"only {total:.1f} mm forecast in {cfg.window_h} h (threshold {cfg.threshold_mm:g} mm)"
        else:
            reason = f"{total:.1f} mm forecast but at most {max_p:.0f}% chance (need {cfg.min_probability:g}%)"
    return Decision(int(now), skip, int(until), round(total, 2), max_p, last_rain, reason)


def command_for(decision, previous):
    """The MQTT command to publish, or None.

    A skip publishes {"action": "skip_auto_water", "until": ...}. When rain drops out of the
    forecast while an earlier skip is still running, "until" is set to now to cancel it.
    """
    if decision.skip:
        return {"action": "skip_auto_water", "until": decision.until}
    if previous and previous.skip and previous.until > decision.ts:
        return {"action": "skip_auto_water", "until": decision.ts}
    return None


class DecisionLog:
    def __init__(self, path, database_url=None):
        self.path = path
        self.db = None
        if database_url:
            import psycopg

            self.db = psycopg.connect(database_url, autocommit=True)
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS irrigation_decisions ("
                " ts TIMESTAMPTZ NOT NULL, node TEXT NOT NULL, skip BOOLEAN NOT NULL,"
                " until TIMESTAMPTZ NOT NULL, rain_mm DOUBLE PRECISION NOT NULL,"
                " max_probability DOUBLE PRECISION NOT NULL, reason TEXT NOT NULL)"
            )

    def write(self, decision, node):
        record = {"date": datetime.fromtimestamp(decision.ts, timezone.utc).isoformat(), "node": node, **asdict(decision)}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        if self.db:
            self.db.execute(
                "INSERT INTO irrigation_decisions VALUES (to_timestamp(%s), %s, %s, to_timestamp(%s), %s, %s, %s)",
                (decision.ts, node, decision.skip, decision.until, decision.rain_mm, decision.max_probability, decision.reason),
            )


def publish(cfg, payload):
    import paho.mqtt.publish as mqtt_publish

    user = os.environ.get("MQTT_USER")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    # TLS for hosted brokers (HiveMQ Cloud, EMQX); on by default for port 8883.
    tls = os.environ.get("MQTT_TLS", "").lower() in ("1", "true", "yes") or port == 8883
    mqtt_publish.single(
        f"greenloop/{cfg.node}/cmd",
        json.dumps(payload),
        qos=1,
        retain=True,
        hostname=os.environ.get("MQTT_HOST", "localhost"),
        port=port,
        auth={"username": user, "password": os.environ.get("MQTT_PASSWORD")} if user else None,
        tls={} if tls else None,
    )


def run_once(cfg, log_, previous):
    forecast = fetch_forecast(cfg)
    decision = decide(forecast, time.time(), cfg)
    log_.write(decision, cfg.node)
    cmd = command_for(decision, previous)
    if cmd:
        publish(cfg, cmd)
    log.info("%s: %s%s", "SKIP" if decision.skip else "water as usual", decision.reason, f" -> published {cmd}" if cmd else "")
    return decision


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = Config.from_env()
    log_ = DecisionLog(os.environ.get("DECISION_LOG", "decisions.jsonl"), os.environ.get("DATABASE_URL"))
    every = float(os.environ.get("CHECK_EVERY_H", "3")) * 3600
    previous = None
    while True:
        try:
            previous = run_once(cfg, log_, previous)
        except Exception:  # keep running through network or broker hiccups
            log.exception("check failed, retrying in 10 min")
            time.sleep(600)
            continue
        if "--once" in sys.argv:
            return
        time.sleep(every)


if __name__ == "__main__":
    main()
