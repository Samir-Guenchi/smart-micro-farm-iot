"""Telegram alert bot: subscribes to the GreenLoop MQTT topics and sends alerts.

Environment:
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  where to send alerts (without them, alerts are only printed)
  MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD
  ALERTS_CONFIG                         path to the thresholds file (default config.toml)
"""

import json
import logging
import os
import threading
import time
import tomllib
import urllib.parse
import urllib.request

import paho.mqtt.client as mqtt

from rules import Config, Rules, utcnow

log = logging.getLogger("alerts")


def send_telegram(token, chat_id, text):
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, data=data, timeout=10) as resp:
                resp.read()
            return True
        except OSError as exc:
            log.warning("telegram send failed (%s), attempt %d", exc, attempt + 1)
            time.sleep(2 * (attempt + 1))
    return False


def load_config():
    path = os.environ.get("ALERTS_CONFIG", "config.toml")
    if not os.path.exists(path):
        log.warning("%s not found, using config.example.toml", path)
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.example.toml")
    with open(path, "rb") as f:
        return Config.from_toml(tomllib.load(f))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        log.warning("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set: alerts will only be logged")

    rules = Rules(load_config(), utcnow())
    lock = threading.Lock()

    def deliver(alerts):
        for alert in alerts:
            log.info("ALERT %s: %s", alert.key, alert.text)
            if token and chat_id:
                send_telegram(token, chat_id, alert.text)

    def on_connect(client, userdata, flags, reason_code, properties):
        log.info("connected to MQTT (%s)", reason_code)
        client.subscribe([("greenloop/+/telemetry", 0), ("greenloop/+/status", 1), ("greenloop/+/event", 1)])

    def on_message(client, userdata, message):
        parts = message.topic.split("/")
        if len(parts) != 3:
            return
        _, node, kind = parts
        text = message.payload.decode("utf-8", errors="replace").strip()
        now = utcnow()
        with lock:
            if kind == "status":
                rules.on_status(node, text.strip('"'), now)
                return
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                return
            if not isinstance(msg, dict):
                return
            if kind == "telemetry":
                rules.on_telemetry(node, msg.get("metrics") or {}, now)
            elif kind == "event":
                rules.on_event(node, msg, now)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="greenloop-alerts")
    if os.environ.get("MQTT_USER"):
        client.username_pw_set(os.environ["MQTT_USER"], os.environ.get("MQTT_PASSWORD"))
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    host, port = os.environ.get("MQTT_HOST", "localhost"), int(os.environ.get("MQTT_PORT", "1883"))
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
    client.loop_start()

    if token and chat_id:
        send_telegram(token, chat_id, "🟢 GreenLoop alert bot started.")
    while True:
        with lock:
            alerts = rules.tick(utcnow())
        deliver(alerts)
        time.sleep(15)


if __name__ == "__main__":
    main()
