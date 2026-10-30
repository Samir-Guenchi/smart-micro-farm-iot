"""Subscribes to the GreenLoop MQTT topics and writes them to TimescaleDB.

Topics (see the MQTT contract in ROADMAP.md / issue #8):
  greenloop/<node>/telemetry  {"ts": ..., "metrics": {"soil_moisture_pct": 41.2, ...}}
  greenloop/<node>/status     "online" | "offline"
  greenloop/<node>/event      {"ts": ..., "type": "door", "state": "closed", ...}
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import psycopg

log = logging.getLogger("ingest")

KNOWN_METRICS = {
    "soil_moisture_pct",
    "air_temp_c",
    "air_humidity_pct",
    "pump_on",
    "water_liters",
    "hive_weight_kg",
    "hive_temp_c",
    "battery_v",
}


def _ts(value):
    """Message timestamp (unix seconds) as an aware datetime; falls back to now."""
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return datetime.now(timezone.utc)


def parse(topic, payload):
    """Turns one MQTT message into a list of (table, row) tuples to write.

    Pure function so it can be tested without a broker or database.
    Unknown topics and malformed payloads return an empty list.
    """
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != "greenloop":
        return []
    _, node, kind = parts
    text = payload.decode("utf-8", errors="replace").strip()

    if kind == "status":
        status = text.strip('"')
        if status not in ("online", "offline"):
            return []
        return [("node_status", {"node": node, "status": status, "last_seen": datetime.now(timezone.utc)})]

    try:
        msg = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(msg, dict):
        return []
    ts = _ts(msg.get("ts"))

    if kind == "telemetry":
        rows = []
        for metric, value in (msg.get("metrics") or {}).items():
            if metric not in KNOWN_METRICS:
                log.warning("unknown metric %s from %s", metric, node)
            try:
                rows.append(("telemetry", {"ts": ts, "node": node, "metric": metric, "value": float(value)}))
            except (TypeError, ValueError):
                continue
        if rows:
            rows.append(("node_status", {"node": node, "status": "online", "last_seen": ts}))
        return rows

    if kind == "event":
        if not msg.get("type"):
            return []
        extra = {k: v for k, v in msg.items() if k not in ("ts", "type", "state", "reason")}
        return [
            ("events", {
                "ts": ts,
                "node": node,
                "type": msg["type"],
                "state": msg.get("state"),
                "reason": msg.get("reason"),
                "data": json.dumps(extra),
            }),
            ("node_status", {"node": node, "status": "online", "last_seen": ts}),
        ]

    return []


SQL = {
    "telemetry": "INSERT INTO telemetry (ts, node, metric, value) VALUES (%(ts)s, %(node)s, %(metric)s, %(value)s)",
    "events": (
        "INSERT INTO events (ts, node, type, state, reason, data) "
        "VALUES (%(ts)s, %(node)s, %(type)s, %(state)s, %(reason)s, %(data)s::jsonb)"
    ),
    # An explicit "offline" always wins; any message from the node marks it online again.
    "node_status": (
        "INSERT INTO node_status (node, status, last_seen) VALUES (%(node)s, %(status)s, %(last_seen)s) "
        "ON CONFLICT (node) DO UPDATE SET status = EXCLUDED.status, "
        "last_seen = GREATEST(node_status.last_seen, EXCLUDED.last_seen)"
    ),
}


def connect_db(url):
    while True:
        try:
            conn = psycopg.connect(url, autocommit=True)
            log.info("connected to database")
            return conn
        except psycopg.OperationalError as exc:
            log.warning("database not ready (%s), retrying in 3 s", exc)
            time.sleep(3)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db = connect_db(os.environ["DATABASE_URL"])

    def on_connect(client, userdata, flags, reason_code, properties):
        log.info("connected to MQTT (%s)", reason_code)
        client.subscribe([("greenloop/+/telemetry", 0), ("greenloop/+/status", 1), ("greenloop/+/event", 1)])

    def on_message(client, userdata, message):
        nonlocal db
        rows = parse(message.topic, message.payload)
        if not rows:
            log.warning("ignored message on %s", message.topic)
            return
        try:
            with db.cursor() as cur:
                for table, row in rows:
                    cur.execute(SQL[table], row)
        except psycopg.OperationalError:
            log.exception("lost database connection, reconnecting")
            db = connect_db(os.environ["DATABASE_URL"])

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="greenloop-ingest")
    if os.environ.get("MQTT_USER"):
        client.username_pw_set(os.environ["MQTT_USER"], os.environ.get("MQTT_PASSWORD"))
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    host = os.environ.get("MQTT_HOST", "localhost")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    # TLS for hosted brokers (HiveMQ Cloud, EMQX); on by default for port 8883.
    if os.environ.get("MQTT_TLS", "").lower() in ("1", "true", "yes") or port == 8883:
        client.tls_set()
    while True:
        try:
            client.connect(host, port, keepalive=60)
            break
        except OSError as exc:
            log.warning("broker not ready (%s), retrying in 3 s", exc)
            time.sleep(3)
    client.loop_forever()


if __name__ == "__main__":
    main()
