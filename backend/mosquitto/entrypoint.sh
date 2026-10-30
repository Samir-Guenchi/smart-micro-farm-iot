#!/bin/sh
# Builds the password file from MQTT_USER / MQTT_PASSWORD on every start,
# so changing .env and restarting is enough to rotate the password.
set -e
if [ -z "$MQTT_USER" ] || [ -z "$MQTT_PASSWORD" ]; then
  echo "MQTT_USER and MQTT_PASSWORD must be set" >&2
  exit 1
fi
rm -f /mosquitto/data/passwd
touch /mosquitto/data/passwd
chmod 0700 /mosquitto/data/passwd
mosquitto_passwd -b /mosquitto/data/passwd "$MQTT_USER" "$MQTT_PASSWORD"
chown mosquitto:mosquitto /mosquitto/data/passwd
exec mosquitto -c /mosquitto/config/mosquitto.conf
