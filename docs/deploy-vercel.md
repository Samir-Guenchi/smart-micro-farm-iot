# Deploying on Vercel

Vercel hosts static sites and short-lived serverless functions. It cannot run
anything that must stay up and listen all the time, so the project splits in
two:

| Part | Vercel? | Why |
|---|---|---|
| `web/` dashboard (PWA) | Yes | Static Vite build. |
| `site/` landing page + crop calendar | Yes (or keep GitHub Pages) | Static files. |
| `assistant/` farming chat (FastAPI) | Yes, as one function | Each question is one short request; it only reads `knowledge/` and `data/`. |
| `backend/` Mosquitto, TimescaleDB, ingest, alerts bot, Grafana | No | MQTT broker, database and ingest must run 24/7. Use a small VPS with `docker compose` (see `backend/README.md`). |
| `backend/api` farm API | Not alone | It is serverless-friendly, but it needs the database and broker above; keep it next to them. |
| `agent/` farm agent | No | `bot` polls Telegram forever; run it on the backend server. |

Each Vercel part is its own Vercel **project** importing the same GitHub repo
with a different **Root Directory**. Every folder has its own `vercel.json`.

## 1. Dashboard (`web/`)

1. Vercel → Add New → Project → import `smart-micro-farm-iot`.
2. Root Directory: `web`. Framework: Vite (detected from `web/vercel.json`).
3. Environment variables:
   - Until the backend is online: `VITE_USE_MOCK=true` (demo data).
   - Once the farm API is hosted: `VITE_API_BASE=https://<your-api-host>` and
     `VITE_USE_MOCK=false`; add the Vercel URL to the API's `CORS_ORIGINS`.
   - Optional: `VITE_VAPID_PUBLIC_KEY` for web push.
4. Deploy. The router uses `#/` URLs, so no rewrites are needed.

## 2. Farming assistant (`assistant/` via `api/index.py`)

1. Add New → Project → same repo.
2. Root Directory: **leave empty** (repository root). The function needs
   `knowledge/` and `data/`, so it is configured by the root `vercel.json`,
   `api/index.py` and `requirements.txt`.
3. Environment variables (Production and Preview):
   - `NVIDIA_API_KEY` = your key from build.nvidia.com (or `ANTHROPIC_API_KEY`)
   - optional `NVIDIA_MODEL` (default `meta/llama-3.3-70b-instruct`)
   - optional `LLM_PROVIDER=nvidia` to force it when both keys are set
4. Deploy, then open `https://<project>.vercel.app/` for the chat page or call
   `POST /api/assistant/chat` with `{"question": "..."}`.
   `GET /api/assistant/health` should list ~30 notes.

## 3. Site (`site/`, optional)

GitHub Pages already publishes it (`.github/workflows/pages.yml`). To move it
to Vercel: new project, Root Directory `site`; `site/vercel.json` runs
`build.sh` and serves `_site/`. Keep "Include files outside the root
directory" on (the default) so `build.sh` can copy `data/`.

## Secrets

Keys go only in Vercel → Project → Settings → Environment Variables, or in a
local `.env` (ignored by git). Never commit them. If a key was ever pasted
somewhere public, revoke it and create a new one.
