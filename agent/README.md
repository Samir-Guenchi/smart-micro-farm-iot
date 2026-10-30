# Farm agent v1

The farming assistant's next step (roadmap Phase 3): an agent that **reads this
farm's data**, **suggests actions**, and lets the **farmer approve** each one.
No autonomous actions in v1.

```
                 ┌───────── read tools ─────────┐
daily check ──► Claude ── list_nodes · get_readings · get_events · get_forecast ──► backend API / Open-Meteo
                 │
                 └─ suggest_watering ──► decision log ──► Telegram [✅ Approve] [❌ Reject]
                                                              │
                                              Approve ──► re-check rules ──► POST /api/nodes/<id>/pump
```

## What it can and cannot do

| | |
|---|---|
| **Read** | Node status and latest values, any metric over the last N hours (summarised: min, max, avg, sum, ≤48 points), door/pump/motion events, a 3-day forecast (rain, rain probability, max temperature, evapotranspiration). |
| **Answer** | "How is the farm today?", "Which bed used the most water this week?", "Did the door close last night?" (`ask` mode has no action tool at all.) |
| **Suggest** | Watering one bed for 1–15 minutes, with its reasoning. Recording a suggestion does nothing to the farm. |
| **Never** | Start the pump without an Approve tap; touch the coop door, the hives or anything involving animals (there is no tool for them, and the suggestion tool refuses non-irrigation nodes); run the pump longer than 15 min (900 s, the same cap as the API and firmware). |

The safety rules are enforced in code (`tools.py`, `approvals.py`), not only in
the prompt: an approved suggestion is checked again right before the pump call.
Suggestions expire after 12 hours and can be decided only once. Telegram taps
are accepted only from `TELEGRAM_CHAT_ID`.

Every suggestion, decision (who, approve/reject/expire) and outcome (pump API
result or error) is appended to `data/decisions.jsonl`. That log is the record
for "the agent's suggestions were right for a few months" before any autonomy
is considered.

The model is Claude by default, or any NVIDIA-hosted model through its
OpenAI-compatible API: set `NVIDIA_API_KEY` (optionally `NVIDIA_MODEL`, default
`meta/llama-3.3-70b-instruct`, which supports tool calls). `LLM_PROVIDER`
forces one provider; see `greenloop_agent/llm.py`.

The agent cannot run on Vercel: the `bot` command polls Telegram forever. Run
it on the same small server as the backend (`docker compose` host or a VPS).

## Run it

```bash
cd agent
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env     # fill in NVIDIA_API_KEY or ANTHROPIC_API_KEY, API_TOKEN, TELEGRAM_*

# Against a week of fake data (no backend needed; pump calls are only recorded)
python -m greenloop_agent --mock ask "Which bed used the most water this week?"
python -m greenloop_agent --mock check

# Against the real backend
python -m greenloop_agent check --send   # report + suggestions to Telegram (run daily, e.g. cron at 18:00)
python -m greenloop_agent bot            # keep running: handles Approve / Reject taps
python -m greenloop_agent log            # print the decision log
```

Switching from the mock to the real API is only `API_BASE_URL` and
`API_TOKEN` (drop `--mock`). A daily cron entry:

```
0 18 * * *  cd /opt/greenloop/agent && .venv/bin/python -m greenloop_agent check --send
```

## Fake data

`fixtures/week.json` is a week of data in the API contract's shapes, generated
by `python fixtures/make_fixtures.py` (fixed seed). It contains a story to test
against: bed 2 dries about twice as fast as bed 1 and used the most water, bed 2
is at 18% now, the coop door missed its close on one night, and the forecast is
dry. Its `irrigation-2` node is fixture-only; the real farm starts with
`irrigation-1`.

## Model

`claude-opus-5-5` at `medium` effort through the Anthropic Python SDK, with a
manual tool loop (thinking blocks are passed back unchanged) and server-side
refusal fallback. Override with `AGENT_MODEL` / `AGENT_EFFORT`.

## Tests

```bash
pytest     # the model is scripted, the farm is the fixture; no keys needed
```

They cover the read tools, the refusal of unsafe suggestions (coop door, hives,
unknown beds, over 15 min), approve/reject/expire/double-tap, pump failures,
the Telegram buttons, and taps from other chats.
