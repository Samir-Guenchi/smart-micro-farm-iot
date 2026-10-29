# Farm API

A small FastAPI service in front of the database and the MQTT broker. The web
dashboard, the assistant and the future farm agent all talk to this API, never
to the database or the broker directly.

Interactive docs (OpenAPI): **`/api/docs`**.

## Endpoints

All under `/api`, JSON, `Authorization: Bearer <token>` (except login).

| Method | Path | Returns |
|---|---|---|
| POST | `/api/login` body `{"username", "password"}` | `{"token": "...", "expires": 1767225600}` |
| GET | `/api/nodes` | `[{"id": "irrigation-1", "status": "online", "last_seen": 1767225600, "latest": {"soil_moisture_pct": 41.2}}]` |
| GET | `/api/readings?node=&metric=&from=&to=` | `[{"ts": 1767225600, "value": 41.2}]` (`from`/`to` in unix seconds, default the last 24 h) |
| GET | `/api/events?node=&type=&limit=` | `[{"ts": ..., "node": "coop-1", "type": "door", "state": "closed"}]` (newest first, default 50, max 500) |
| POST | `/api/nodes/<id>/pump` body `{"duration_s": 600}` | `202 {"ok": true, "duration_s": 600}` |

- A node is reported `offline` if it said so or has sent nothing for
  `OFFLINE_AFTER_S` (10 min).
- `POST /pump` publishes `{"action": "pump", "duration_s": N}` to
  `greenloop/<id>/cmd` (QoS 1). `duration_s` is capped at `MAX_PUMP_S` (900 s),
  the same hard limit the firmware enforces. Only nodes in `PUMP_NODES` accept
  it (404 otherwise); 503 if the broker can't be reached.

## Auth

To start there is one admin account from `API_ADMIN_USER` / `API_ADMIN_PASSWORD`.
`POST /api/login` returns a signed token valid for `API_TOKEN_HOURS` (30 days).
Services that can't log in (alert bot, assistant) can use a fixed
`API_SERVICE_TOKEN`. A proper user table can replace `auth.check_password`
later (Phase 2, outside farmers) without changing the endpoints.

## Run

```bash
cd backend/api
pip install -r requirements.txt
cp .env.example .env    # fill in passwords and API_SECRET_KEY
set -a; . ./.env; set +a
uvicorn main:app --reload
```

Then open <http://localhost:8000/api/docs>, call `/api/login`, press
**Authorize** and paste the token.

No sensors yet? Fill the database with a day of fake data:

```bash
python seed.py
```

Quick check from the terminal:

```bash
TOKEN=$(curl -s localhost:8000/api/login -H 'content-type: application/json' \
  -d '{"username":"admin","password":"..."}' | python -c 'import json,sys; print(json.load(sys.stdin)["token"])')
curl -s localhost:8000/api/nodes -H "Authorization: Bearer $TOKEN"
curl -s -X POST localhost:8000/api/nodes/irrigation-1/pump -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d '{"duration_s": 600}'
```

With Docker, next to the rest of the backend stack in `backend/docker-compose.yml`:

```yaml
  api:
    build: ./api
    restart: unless-stopped
    depends_on: [db, mosquitto]
    env_file: ./api/.env
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      MQTT_HOST: mosquitto
    ports:
      - "8000:8000"
```

## Tests

```bash
python -m pytest -q
```

The tests replace the database and broker with fakes, so they need neither.
