# Backend: data pipeline

One `docker compose up` gives the whole Phase 0 pipeline:

```
ESP32 nodes / simulator ──MQTT──▶ Mosquitto ──▶ ingest ──▶ TimescaleDB ──▶ Grafana
```

| Service | What it does | Port |
|---|---|---|
| `mosquitto` | MQTT broker, username/password auth (no anonymous access) | 1883 |
| `db` | Postgres 16 + TimescaleDB, schema in [`db/init.sql`](db/init.sql) | 5432 (localhost only) |
| `ingest` | Subscribes to `greenloop/+/telemetry`, `status` and `event` and writes them to the database ([`ingest/ingest.py`](ingest/ingest.py)) | none |
| `grafana` | "Farm overview" dashboard, provisioned automatically | 3000 |
| `simulator` | Fake data for `irrigation-1`, `hive-1`, `coop-1` (optional, `sim` profile) | none |

Topics and payloads follow the shared MQTT contract in [ROADMAP.md](../ROADMAP.md)
and issue #8.

## Run locally

Needs Docker with the compose plugin.

```bash
cd backend
cp .env.example .env          # then edit the passwords
docker compose --profile sim up -d --build
```

Open <http://localhost:3000>, log in with `GRAFANA_ADMIN_USER` /
`GRAFANA_ADMIN_PASSWORD` from `.env`, and the **Farm overview** dashboard is the
home page: node status and last seen, coop door, pump state, soil moisture,
temperature, pump history, hive weight and recent events.

Once real boards are publishing, run without the simulator:

```bash
docker compose --profile sim stop simulator
```

### Simulator

`simulator.py` publishes realistic readings every 60 s: soil dries during the
day and the pump auto-waters below 30 %, temperature follows the time of day,
the hive gains weight while bees forage, and the coop door opens at 07:00 and
closes at 19:00. It also obeys pump commands on `greenloop/irrigation-1/cmd`
(capped at 900 s like the firmware), so the API's pump button can be tested
end to end.

Run it outside Docker for a faster demo:

```bash
pip install paho-mqtt
python simulator.py --user greenloop --password <MQTT_PASSWORD> --interval 5
```

### Poke the broker by hand

```bash
mosquitto_sub -u greenloop -P <MQTT_PASSWORD> -t 'greenloop/#' -v
mosquitto_pub -u greenloop -P <MQTT_PASSWORD> -t greenloop/coop-1/event -q 1 \
  -m '{"ts": '"$(date +%s)"', "type": "door", "state": "closed"}'
```

### Query the data

```bash
docker compose exec db psql -U greenloop -c \
  "SELECT node, metric, value, ts FROM telemetry ORDER BY ts DESC LIMIT 10"
```

Tables: `telemetry` (one row per metric per message), `events` (door, pump,
motion) and `node_status` (online/offline and last seen per node).

## Run on Render

The root [`render.yaml`](../render.yaml) Blueprint runs the API, the assistant,
the workers (ingest, alerts, weather, agent) and a managed Postgres on Render,
with a hosted MQTT broker instead of Mosquitto. Steps: [docs/deploy.md](../docs/deploy.md).

## Run on a small VPS

A 1 vCPU / 1–2 GB VPS (Hetzner CX22, a DigitalOcean basic droplet or similar)
is enough for one farm.

1. Install Docker: `curl -fsSL https://get.docker.com | sh`
2. Clone the repo, `cd backend`, `cp .env.example .env` and set **strong**
   passwords. The broker is exposed to the internet so the nodes can reach it.
3. `docker compose up -d --build` (no simulator).
4. Open only what is needed in the firewall:
   ```bash
   ufw allow OpenSSH && ufw allow 1883/tcp && ufw allow 3000/tcp && ufw enable
   ```
   Postgres is bound to `127.0.0.1` and stays private.
5. Point the ESP32 `secrets.h` at the VPS IP or domain with the same MQTT
   username and password.

Before real use, put Grafana behind HTTPS (Caddy or nginx with Let's Encrypt)
and switch MQTT to TLS on port 8883.

## Tests

```bash
cd backend/ingest
pip install -r requirements.txt pytest
python -m pytest -q
```

CI runs the tests of every `backend/*/tests` folder on each pull request.
