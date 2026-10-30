# Deploying: backend on Render, frontend on Vercel

Everything that runs on a server lives in `backend/` and is hosted on
[Render](https://render.com). Everything that runs in the browser lives in
`frontend/` and is hosted on [Vercel](https://vercel.com). No backend part
needs a file outside `backend/`.

| Part | Where | How |
|---|---|---|
| `backend/api` farm REST API | Render web service `greenloop-api` | `render.yaml` |
| `backend/assistant` farming chat (+ `backend/knowledge`, `backend/data`) | Render web service `greenloop-assistant` | `render.yaml` |
| `backend/ingest`, `alerts`, `weather`, `agent` | Render background workers | `render.yaml` |
| Database (Postgres) | Render Postgres `greenloop-db` | `render.yaml`; schema applied by the API on start |
| MQTT broker | Hosted broker, e.g. HiveMQ Cloud (free) | Render only accepts HTTP from outside, so Mosquitto cannot run there |
| Grafana | Optional: local `docker compose` or Grafana Cloud | Not in the Blueprint |
| `frontend/web` dashboard (PWA) | Vercel, Root Directory `frontend/web` | `frontend/web/vercel.json` |
| `frontend/site` landing page + crop calendar | Vercel, Root Directory `frontend/site` (or GitHub Pages) | `frontend/site/vercel.json` |

## 1. MQTT broker (before Render)

1. Create a free cluster on HiveMQ Cloud (or EMQX Serverless).
2. Add a username and password for the farm.
3. Note the host (`xxxx.s1.eu.hivemq.cloud`) and port **8883** (TLS). Every
   backend service turns TLS on by itself for port 8883 (or set `MQTT_TLS=true`).
4. The ESP32 nodes publish to the same broker with TLS.

## 2. Backend on Render

1. Render → **New → Blueprint** → connect GitHub → pick `smart-micro-farm-iot`.
   Render reads `render.yaml` from the repository root.
2. Render lists the database and the six services. Background workers have no
   free plan; remove the ones you don't need yet (for a first test keep only
   `greenloop-db`, `greenloop-api` and `greenloop-assistant`).
3. Fill in the values Render asks for (`sync: false` in the file):
   - `MQTT_HOST`, `MQTT_USER`, `MQTT_PASSWORD` from step 1
   - `API_ADMIN_PASSWORD` (dashboard login)
   - `NVIDIA_API_KEY` (or `ANTHROPIC_API_KEY`)
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` for alerts and the agent
   - `CORS_ORIGINS`: leave empty for now, set it in step 4
   - `API_BASE_URL` (agent): `https://<greenloop-api>.onrender.com/api`
4. **Apply**. When it is live, check:
   - `https://<greenloop-api>.onrender.com/api/health` → `{"ok": true}`
   - `https://<greenloop-assistant>.onrender.com/api/assistant/health` → ~30 notes
   - `https://<greenloop-assistant>.onrender.com/` → chat page

Free web services sleep after 15 minutes without traffic; the first request
after that takes about a minute. A free Postgres expires after 30 days, so
move it to a paid plan before real use.

## 3. Frontend on Vercel

### Dashboard (`frontend/web`)

1. Vercel → Add New → Project → import `smart-micro-farm-iot`.
2. Root Directory: `frontend/web`. Framework: Vite.
3. Environment variables:
   - `VITE_API_BASE` = `https://<greenloop-api>.onrender.com`
   - `VITE_USE_MOCK` = `false` (or `true` for demo data until the API is up)
   - optional `VITE_VAPID_PUBLIC_KEY` for web push
4. Deploy, then put the Vercel URL into `CORS_ORIGINS` of `greenloop-api` on
   Render (comma-separated if there are several).

### Site (`frontend/site`, optional)

GitHub Pages already publishes it. To use Vercel instead: new project, Root
Directory `frontend/site`. `build.sh` copies the crop calendar from
`backend/data/`, so keep "Include files outside the root directory" on (the
default).

## Secrets

Keys go only in Render / Vercel environment variables, or in a local `.env`
(ignored by git). Never commit them. If a key was ever pasted somewhere public,
revoke it and create a new one.
