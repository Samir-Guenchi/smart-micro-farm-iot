"""Fills the database with 24 h of fake readings and events, for API development.

    DATABASE_URL=postgresql://greenloop:...@localhost/greenloop python seed.py

Creates the tables if they don't exist (same schema as backend/db/init.sql,
without the TimescaleDB extras), so it also works on a plain Postgres.
"""

import json
import math
import os
import random
from datetime import datetime, timedelta, timezone

import psycopg

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (ts TIMESTAMPTZ NOT NULL, node TEXT NOT NULL, metric TEXT NOT NULL, value DOUBLE PRECISION NOT NULL);
CREATE TABLE IF NOT EXISTS events (ts TIMESTAMPTZ NOT NULL, node TEXT NOT NULL, type TEXT NOT NULL, state TEXT, reason TEXT, data JSONB NOT NULL DEFAULT '{}'::jsonb);
CREATE TABLE IF NOT EXISTS node_status (node TEXT PRIMARY KEY, status TEXT NOT NULL, last_seen TIMESTAMPTZ NOT NULL);
"""


def main():
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    telemetry, events = [], []
    soil = 48.0
    for i in range(24 * 60, -1, -5):
        ts = now - timedelta(minutes=i)
        hour = ts.hour + ts.minute / 60
        temp = 14 + 8 * math.sin((hour - 9) / 24 * 2 * math.pi) + random.gauss(0, 0.3)
        soil -= 0.25
        pump = 0
        if soil < 30:
            events.append((ts, "irrigation-1", "pump", "started", "auto", json.dumps({"duration_s": 300})))
            events.append((ts + timedelta(minutes=5), "irrigation-1", "pump", "stopped", "done", "{}"))
            soil, pump = 50.0, 1
        telemetry += [
            (ts, "irrigation-1", "soil_moisture_pct", round(soil + random.gauss(0, 0.4), 1)),
            (ts, "irrigation-1", "air_temp_c", round(temp, 1)),
            (ts, "irrigation-1", "pump_on", pump),
            (ts, "hive-1", "hive_weight_kg", round(38 + (24 * 60 - i) / 1440 * 0.6, 2)),
            (ts, "hive-1", "hive_temp_c", round(34.5 + random.gauss(0, 0.3), 1)),
            (ts, "coop-1", "air_temp_c", round(temp + 2, 1)),
        ]
    for day in (1, 0):
        base = (now - timedelta(days=day)).replace(minute=0)
        events.append((base.replace(hour=7), "coop-1", "door", "open", None, "{}"))
        events.append((base.replace(hour=19), "coop-1", "door", "closed", None, "{}"))
    events = [e for e in events if e[0] <= now]

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(SCHEMA)
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO telemetry VALUES (%s, %s, %s, %s)", telemetry)
            cur.executemany("INSERT INTO events VALUES (%s, %s, %s, %s, %s, %s::jsonb)", events)
            for node in ("irrigation-1", "hive-1", "coop-1"):
                cur.execute(
                    "INSERT INTO node_status VALUES (%s, 'online', %s) ON CONFLICT (node) DO UPDATE SET status = 'online', last_seen = EXCLUDED.last_seen",
                    (node, now),
                )
    print(f"inserted {len(telemetry)} readings and {len(events)} events")


if __name__ == "__main__":
    main()
