"""Generate fixtures/week.json: one week of fake farm data in the API contract's shapes.

  python fixtures/make_fixtures.py

Deterministic (fixed seed), so tests can assert on it. The story in the data:
- Bed 2 (irrigation-2) dries about twice as fast as bed 1 and used the most water.
- The coop door did not close on the night of day 5.
- The forecast is dry for the next three days.
"""
import json
import math
import random
from pathlib import Path

random.seed(7)
END = 1814832000  # 2027-07-05 00:00 UTC, mid-summer
START = END - 7 * 86400
HOUR = 3600

readings = {}  # "node|metric" -> [{"ts", "value"}]
events = []


def put(node, metric, ts, value):
    readings.setdefault(f"{node}|{metric}", []).append({"ts": ts, "value": round(value, 2)})


for node, dry_rate, start_moisture, threshold in [("irrigation-1", 0.18, 38, 25), ("irrigation-2", 0.36, 34, 25)]:
    m = start_moisture
    for ts in range(START, END, HOUR):
        hour = (ts // HOUR) % 24
        day_factor = 1.6 if 9 <= hour <= 18 else 0.5  # dries faster in the day
        m -= dry_rate * day_factor + random.uniform(-0.03, 0.03)
        pump = 0
        liters = 0.0
        if m < threshold and hour == 5:  # the firmware rule waters at dawn below threshold
            duration = 600
            m += 14
            pump = 1
            liters = 42.0 if node == "irrigation-1" else 46.0
            events.append({"ts": ts, "node": node, "type": "pump", "state": "started", "reason": "threshold"})
            events.append({"ts": ts + duration, "node": node, "type": "pump", "state": "stopped", "reason": "duration"})
        put(node, "soil_moisture_pct", ts, m)
        put(node, "pump_on", ts, pump)
        put(node, "water_liters", ts, liters)
        temp = 19 + 7 * math.sin((hour - 9) / 24 * 2 * math.pi) + random.uniform(-0.5, 0.5)
        put(node, "air_temp_c", ts, temp)
        put(node, "air_humidity_pct", ts, 70 - 20 * math.sin((hour - 9) / 24 * 2 * math.pi) + random.uniform(-2, 2))
        put(node, "battery_v", ts, 4.05 - (ts - START) / (7 * 86400) * 0.08)

w = 41.0
for ts in range(START, END, HOUR):
    hour = (ts // HOUR) % 24
    w += 0.12 if 10 <= hour <= 17 else -0.03  # nectar flow by day, consumption at night
    put("hive-1", "hive_weight_kg", ts, w)
    put("hive-1", "hive_temp_c", ts, 34.8 + random.uniform(-0.4, 0.4))
    put("hive-1", "battery_v", ts, 3.95)

for day in range(7):
    base = START + day * 86400
    events.append({"ts": base + 4 * HOUR + 40 * 60, "node": "coop-1", "type": "door", "state": "open"})
    if day != 5:  # the door missed its close on day 5 (2027-07-03 evening)
        events.append({"ts": base + 20 * HOUR + 55 * 60, "node": "coop-1", "type": "door", "state": "closed"})
events.append({"ts": START + 3 * 86400 + 14 * HOUR, "node": "coop-1", "type": "motion", "state": "detected"})
events.sort(key=lambda e: e["ts"])

nodes = []
for node in ["irrigation-1", "irrigation-2", "hive-1", "coop-1"]:
    latest = {k.split("|")[1]: v[-1]["value"] for k, v in readings.items() if k.startswith(node + "|")}
    if node == "coop-1":
        latest = {"battery_v": 3.9}
    nodes.append({"id": node, "status": "online", "last_seen": END - 60, "latest": latest})

forecast = {
    "daily": {
        "time": ["2027-07-05", "2027-07-06", "2027-07-07"],
        "precipitation_sum": [0.0, 0.2, 0.0],
        "precipitation_probability_max": [5, 15, 10],
        "temperature_2m_max": [27.5, 28.9, 26.1],
        "et0_fao_evapotranspiration": [5.1, 5.4, 4.8],
    }
}

out = {"now": END, "nodes": nodes, "readings": readings, "events": events, "forecast": forecast}
Path(__file__).with_name("week.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print("wrote week.json:", sum(len(v) for v in readings.values()), "readings,", len(events), "events")
