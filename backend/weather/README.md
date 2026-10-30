# Weather-aware irrigation

Skips the irrigation node's automatic watering when rain is coming, using the
free [Open-Meteo](https://open-meteo.com/) forecast (no API key).

Every 3 hours the service reads the hourly forecast for the farm's coordinates
and looks at the next 24 h:

- **Skip** if at least `RAIN_THRESHOLD_MM` (5 mm) is forecast **and** at least
  one hour has a precipitation probability of `RAIN_MIN_PROBABILITY` (60 %) or
  more. It publishes a **retained** message to `greenloop/irrigation-1/cmd`:
  ```json
  {"action": "skip_auto_water", "until": 1767312000}
  ```
  `until` is the end of the 24 h window, or 6 h after the last rainy hour if
  that is later (wet soil), and never more than 36 h ahead.
- **Water as usual** otherwise. If an earlier skip is still running but the rain
  has dropped out of the forecast, it publishes `until` = now to cancel it.

Because the message is retained, a node that reconnects gets the current
decision straight away. Manual pump commands from the dashboard are not
affected; only automatic watering is skipped. The firmware side is a small
`skip_auto_water` handler on the irrigation node (the simulator in `backend/`
already honours it).

## Decision log

Every check is logged, skipped or not, so skipped days can be compared with
water use later:

- `decisions.jsonl`, one JSON object per line: date, forecast rain (mm), max
  probability, skip, until, reason.
- If `DATABASE_URL` is set, also the `irrigation_decisions` table (created
  automatically), next to the `telemetry` table with `water_liters`.

## Configuration

| Variable | Default | |
|---|---|---|
| `FARM_LATITUDE`, `FARM_LONGITUDE` | required | the farm's coordinates |
| `RAIN_THRESHOLD_MM` | `5` | rain in the window needed to skip |
| `RAIN_MIN_PROBABILITY` | `60` | % chance needed in at least one hour |
| `FORECAST_WINDOW_H` | `24` | look-ahead |
| `CHECK_EVERY_H` | `3` | how often to check |
| `IRRIGATION_NODE` | `irrigation-1` | |
| `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASSWORD` | `localhost`, `1883` | broker |
| `DECISION_LOG` | `decisions.jsonl` | log file |
| `DATABASE_URL` | unset | optional Postgres log |

## Run

```bash
cd backend/weather
pip install -r requirements.txt
export FARM_LATITUDE=56.95 FARM_LONGITUDE=24.11 MQTT_USER=greenloop MQTT_PASSWORD=...
python weather.py --once     # one check, then exit
python weather.py            # keep checking every 3 h
```

With Docker, next to the rest of the backend stack in `backend/docker-compose.yml`:

```yaml
  weather:
    build: ./weather
    restart: unless-stopped
    depends_on: [mosquitto]
    environment:
      FARM_LATITUDE: "56.95"
      FARM_LONGITUDE: "24.11"
      MQTT_HOST: mosquitto
      MQTT_USER: ${MQTT_USER}
      MQTT_PASSWORD: ${MQTT_PASSWORD}
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    volumes:
      - ./weather/logs:/app/logs
```

## Tests

```bash
python -m pytest -q
```
