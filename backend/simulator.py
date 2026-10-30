"""Publishes realistic fake data for irrigation-1, hive-1 and coop-1.

Lets the whole pipeline (ingest, Grafana, alerts, API) run before the real
boards are installed. Follows the MQTT contract in ROADMAP.md / issue #8.

    python simulator.py --host localhost --user greenloop --password change-me-mqtt
    python simulator.py --interval 5   # faster than the real 60 s, for demos

It also listens on greenloop/irrigation-1/cmd, so pump commands from the API
start the simulated pump.
"""

import argparse
import json
import math
import os
import random
import time
from datetime import datetime

import paho.mqtt.client as mqtt

MAX_PUMP_S = 900  # same hard limit the irrigation firmware enforces
AUTO_WATER_BELOW = 30.0
AUTO_WATER_S = 300


class Farm:
    def __init__(self, interval):
        self.interval = interval
        self.soil = 45.0
        self.pump_until = 0.0
        self.water_liters = 0.0
        self.hive_weight = 38.0
        self.door = None
        self.skip_auto_until = 0.0

    def start_pump(self, duration_s, reason, now):
        duration_s = max(1, min(int(duration_s), MAX_PUMP_S))
        self.pump_until = now + duration_s
        return {"ts": int(now), "type": "pump", "state": "started", "reason": reason, "duration_s": duration_s}

    def step(self, now):
        """Advances the farm by one interval. Returns (telemetry by node, events by node)."""
        events = {"irrigation-1": [], "hive-1": [], "coop-1": []}
        hour = datetime.fromtimestamp(now).hour + datetime.fromtimestamp(now).minute / 60
        # Warmer, drier air in the afternoon.
        temp = 14 + 8 * math.sin((hour - 9) / 24 * 2 * math.pi) + random.gauss(0, 0.3)
        humidity = max(25.0, min(95.0, 70 - 1.8 * (temp - 14) + random.gauss(0, 1.5)))

        pumping = now < self.pump_until
        if pumping:
            self.soil = min(80.0, self.soil + 0.9 * self.interval / 60)
            self.water_liters += 4.0 * self.interval / 60  # ~4 L/min drip line
        else:
            if self.pump_until and now - self.interval < self.pump_until <= now:
                events["irrigation-1"].append({"ts": int(now), "type": "pump", "state": "stopped", "reason": "done"})
            self.soil = max(10.0, self.soil - (0.04 + max(0.0, temp - 15) * 0.01) * self.interval / 60)
            if self.soil < AUTO_WATER_BELOW and now >= self.skip_auto_until:
                events["irrigation-1"].append(self.start_pump(AUTO_WATER_S, "auto", now))
                pumping = True

        # Bees bring nectar in during the day; the hive loses a little weight overnight.
        self.hive_weight += (0.002 if 9 <= hour < 18 else -0.0008) * self.interval / 60

        door = "open" if 7 <= hour < 19 else "closed"
        if door != self.door:
            if self.door is not None:
                events["coop-1"].append({"ts": int(now), "type": "door", "state": door})
            self.door = door

        telemetry = {
            "irrigation-1": {
                "soil_moisture_pct": round(self.soil + random.gauss(0, 0.4), 1),
                "air_temp_c": round(temp, 1),
                "air_humidity_pct": round(humidity, 1),
                "pump_on": 1 if pumping else 0,
                "water_liters": round(self.water_liters, 2),
                "battery_v": round(4.1 + random.gauss(0, 0.02), 2),
            },
            "hive-1": {
                "hive_weight_kg": round(self.hive_weight + random.gauss(0, 0.02), 2),
                "hive_temp_c": round(34.5 + random.gauss(0, 0.3), 1),
                "air_temp_c": round(temp + random.gauss(0, 0.2), 1),
                "air_humidity_pct": round(humidity + random.gauss(0, 1), 1),
                "battery_v": round(3.95 + random.gauss(0, 0.02), 2),
            },
            "coop-1": {
                "air_temp_c": round(temp + 2 + random.gauss(0, 0.2), 1),
                "battery_v": round(4.0 + random.gauss(0, 0.02), 2),
            },
        }
        return telemetry, events


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default=os.environ.get("MQTT_HOST", "localhost"))
    p.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    p.add_argument("--user", default=os.environ.get("MQTT_USER"))
    p.add_argument("--password", default=os.environ.get("MQTT_PASSWORD"))
    p.add_argument("--interval", type=float, default=60, help="seconds between telemetry messages (default 60)")
    args = p.parse_args()

    farm = Farm(args.interval)
    nodes = ["irrigation-1", "hive-1", "coop-1"]
    clients = {}

    def on_cmd(client, userdata, message):
        try:
            cmd = json.loads(message.payload)
        except json.JSONDecodeError:
            return
        if not isinstance(cmd, dict):
            return
        now = time.time()
        if cmd.get("action") == "pump":
            event = farm.start_pump(cmd.get("duration_s", 60), "manual", now)
            client.publish("greenloop/irrigation-1/event", json.dumps(event), qos=1)
            print(f"pump command: running {event['duration_s']} s")
        elif cmd.get("action") == "skip_auto_water":
            farm.skip_auto_until = float(cmd.get("until", 0))
            print(f"auto watering skipped until {farm.skip_auto_until:.0f}")

    for node in nodes:
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-{node}")
        if args.user:
            c.username_pw_set(args.user, args.password)
        c.will_set(f"greenloop/{node}/status", "offline", qos=1, retain=True)
        if node == "irrigation-1":
            c.on_connect = lambda cl, *_: cl.subscribe("greenloop/irrigation-1/cmd", qos=1)
            c.on_message = on_cmd
        while True:
            try:
                c.connect(args.host, args.port, keepalive=60)
                break
            except OSError as exc:
                print(f"broker not ready ({exc}), retrying in 3 s")
                time.sleep(3)
        c.loop_start()
        c.publish(f"greenloop/{node}/status", "online", qos=1, retain=True)
        clients[node] = c

    print(f"simulating {', '.join(nodes)} every {args.interval:g} s on {args.host}:{args.port}")
    try:
        while True:
            now = time.time()
            telemetry, events = farm.step(now)
            for node in nodes:
                for event in events[node]:
                    clients[node].publish(f"greenloop/{node}/event", json.dumps(event), qos=1)
                clients[node].publish(
                    f"greenloop/{node}/telemetry", json.dumps({"ts": int(now), "metrics": telemetry[node]}), qos=0
                )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        for node, c in clients.items():
            c.publish(f"greenloop/{node}/status", "offline", qos=1, retain=True).wait_for_publish(2)
            c.loop_stop()


if __name__ == "__main__":
    main()
