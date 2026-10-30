# GreenLoop Farm roadmap

This is the build plan behind the [roadmap in the README](README.md#roadmap). It
turns the 2026–2028 milestones into phases with concrete deliverables, answers
two open questions (web or mobile app first, and when an AI agent can be added),
and lines each phase up with the yearly residence permit renewal, which needs a
progress report.

*Last updated: 29 October 2026.*

---

## The short answers

**Web or app?** Build a **web dashboard first and make it a Progressive Web App
(PWA)**. A PWA is a website that can be installed on a phone's home screen, opens
full screen like an app, works on Android and iPhone from one codebase, and can
send push notifications. That gives "run from a phone" from day one for the cost
of one project instead of three (web, Android, iOS). Build a **native mobile app
only later (2028)**, and only if users hit a real limit of the PWA, such as
offline use in fields with no signal, Bluetooth pairing with sensors, or store
presence for partner farms.

**When can an AI agent be added?** In two steps:

1. **AI farming assistant (Phase 2, Q1–Q2 2027).** A chat assistant that answers
   farming questions from a curated knowledge base. It needs no sensors, only
   the founder's notes and the crop calendar, so it can start as soon as the
   dashboard exists.
2. **Farm agent (Phase 3, from Q3 2027).** An assistant that also reads the
   farm's live data and can act: "Bed 2 is drying faster than usual and no rain
   is forecast, I suggest 20 minutes of watering tonight. Approve?" This needs
   the backend, an API, alerts and at least one growing season of sensor data
   first, so it comes after those are in place. It starts by **suggesting**,
   with the farmer approving each action, and only gets to act on its own for
   low-risk actions once it has proven reliable.

---

## Phases at a glance

| Phase | When | Goal | Main deliverables |
|---|---|---|---|
| **0. Prove it works** | Nov – Dec 2026 | Real sensor data on a screen | Firmware, BOM, MQTT backend, Grafana dashboard, Telegram alerts |
| **1. Web dashboard MVP** | Jan – Mar 2027 | The 2026 platform MVP, usable by the farmer every day | Custom web dashboard as a PWA, crop calendar, camera and coop door status |
| **2. Assistant and first users** | Apr – Jun 2027 | Something other farmers can use | AI farming assistant, accounts, multilingual setup, shop and bookings via ready-made tools |
| **3. Farm agent** | Jul – Dec 2027 | The assistant understands this farm | Agent with read access to farm data, suggested actions with approval, weather-aware irrigation, paid tier |
| **4. Scale and ML** | 2028 | A model other farms can license | Prediction models, multi-farm support, Arabic / French / English, native app if needed |

Dates assume the current small team (founder, a software engineering student
and a software engineer). If the team grows, phases 1 and 2 can overlap.

---

## Phase 0: Prove it works (Nov – Dec 2026)

The goal is that the README stops being a plan and becomes a demo.

- **Firmware** in `firmware/`, one PlatformIO project per ESP32 node:
  irrigation node (soil moisture, temperature, humidity, pump relay), hive node,
  coop node (reed switch on the Okköbi door to report open/closed).
- **Hardware docs** in `hardware/`: wiring diagrams, bill of materials with
  prices, solar sizing.
- **Backend:** nodes publish over MQTT to a broker (Mosquitto or a hosted one),
  readings stored in a time-series database (InfluxDB, or Postgres with
  TimescaleDB).
- **Dashboard day one:** Grafana on top of the database. No custom code needed
  yet.
- **Alerts:** a Telegram bot for "bed too dry", "door did not close at sunset",
  "node offline" and "pump running too long". This delivers phone alerts with no
  app at all.
- **Repo basics:** `.gitignore`, `secrets.example.h`, a license, CI that builds
  the firmware, and a monthly entry in a progress log.

**Done when:** soil readings from the field show up live on a chart, and a dry
bed sends a Telegram message.

## Phase 1: Web dashboard MVP (Jan – Mar 2027)

The custom platform starts here. Grafana stays as the internal tool.

- **Web dashboard** in `frontend/web/`: live readings per bed, pump on/off with a manual
  button, coop door state, last-seen per node, history charts.
- **PWA from the start:** installable on the phone, push notifications next to
  the Telegram ones.
- **Backend API** in `backend/`: a small REST API in front of the database, with
  login. Everything later (assistant, agent, apps) talks to this API, never to
  the database directly.
- **Crop calendar:** a dataset (Latvia, Algeria, France, Sweden, Morocco × 12
  months × crops) in `backend/data/` and a page to browse it.
- **Camera:** live stream in the dashboard if the camera exposes RTSP or ONVIF,
  and motion snapshots in alerts.
- **Translations ready:** set up i18n in the web app now, even if only English
  ships, so Arabic and French are a translation job later and not a rewrite.

**Done when:** the farmer checks the farm and waters a bed from the phone,
without opening Grafana or Telegram.

## Phase 2: Assistant and first users (Apr – Jun 2027)

This is when the **first AI piece** arrives.

- **AI farming assistant:** a chat page in the web app backed by a large
  language model, with retrieval over a curated knowledge base (`backend/knowledge/`,
  markdown notes from the founder's expertise) and the crop calendar. It answers
  general questions: diseases, soil, companion planting, what to sow this month
  in a given country.
- **Accounts and a free tier**, so outside farmers can sign up. This is the start
  of the "500+ assistant users" goal for 2027.
- **Farm shop and agri-tourism bookings** with ready-made tools (Shopify or
  WooCommerce, Cal.com) linked from the site, not custom code.
- **Irrigation logging:** liters used per bed per day, the data behind the
  "up to 60% water saving" claim.

**Done when:** an outside farmer can sign up and get a useful answer from the
assistant, and the farm has its first online order or booking.

## Phase 3: Farm agent (Jul – Dec 2027)

The assistant becomes an **agent**: it knows this farm, not just farming.

**What it needs first** (all from earlier phases):

| Requirement | Why | Comes from |
|---|---|---|
| Reliable sensor data, ideally a full growing season | The agent can only reason about what it can measure | Phase 0, collected since late 2026 |
| A backend API with clear read and control endpoints | The agent acts through tools, never by touching hardware directly | Phase 1 |
| Alerts and event history | So it can explain *why* it suggests something | Phases 0–1 |
| Water-use logs and weather forecast | To decide whether watering is worth it | Phase 2, plus a free forecast API such as Open-Meteo |
| Safety limits in firmware | Maximum pump run time, door schedule bounds; enforced on the ESP32 so no software bug can override them | Phase 0 firmware, tightened here |

**How it is introduced, step by step:**

1. **Read only.** The agent can answer "how is the farm today?", "which bed used
   the most water this week?", "did the door close last night?".
2. **Suggest and approve.** It proposes actions (water bed 2 for 20 minutes, skip
   tomorrow's watering because rain is forecast) and the farmer taps approve or
   reject in the app or on Telegram. Every suggestion and decision is logged.
3. **Act alone on low-risk actions.** Only after the suggestions have been right
   for a few months, and only for actions with firmware limits behind them, like
   short watering runs. Anything involving animals or the coop door stays
   approval-only.

Also in this phase:

- **Weather-aware irrigation** in the backend rules, which the agent builds on.
- **Paid tier for professional farmers**, where the farm agent (connected to
  their own sensors) is the main paid feature.

**Done when:** the agent sends a useful, correct suggestion the farmer did not
think of, and the farmer approves it from the phone.

## Phase 4: Scale and ML (2028)

- **Prediction models** trained on the farm's own data: soil drying rate for
  smarter irrigation, hive weight trends for harvest readiness, sound-based
  swarming detection. This is the "AI yield prediction and water optimization"
  milestone, and it needs the data collected since 2026.
- **Multi-farm support:** partner farms in North Africa and Southern Europe run
  the same firmware and connect to their own space on the platform, the basis for
  licensing the model.
- **Arabic, French and English** versions of the web app and assistant.
- **Native mobile app (only if needed):** if partner farms need offline use,
  Bluetooth setup of nodes or app store presence, build one with Flutter or React
  Native on the same backend API. If the PWA is enough, skip it.

---

## Permit renewal checkpoints

The residence permit is renewed every year with a progress report. Each renewal
should be able to point at working, visible results in this repo.

| Renewal | What the progress report can show |
|---|---|
| **First renewal (2027)** | Company registered; firmware and hardware docs in the repo; live dashboard with real field data; alerts working; crop calendar online; assistant in beta; first shop orders and farm visits |
| **Second renewal (2028)** | Assistant users and paid subscribers; farm agent in use with logged suggestions; a full season of water-use data supporting the savings claim; first export buyer |
| **Third renewal (2029)** | Revenue toward 100k+ EUR; partner farms running the platform; multilingual product; ML models in production |

The monthly progress log (Phase 0) is what makes writing each report quick.

---

## Order of work if time is short

If only a few things get done, do them in this order, because each one depends
on the one before:

1. Firmware sending real readings.
2. Data landing in a database, visible in Grafana.
3. Telegram alerts.
4. Web dashboard as a PWA.
5. AI assistant (knowledge only).
6. Farm agent (reads data, suggests, farmer approves).
7. Native app, only if the PWA is not enough.
