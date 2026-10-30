# Contributing

Thanks for helping build GreenLoop Farm. This file is the short version of how
we work; [ROADMAP.md](ROADMAP.md) says what we are building and in what order.

## How work is organised

- Every piece of work is a **GitHub issue**, labelled with a phase
  (`phase-0` … `phase-4`) and a track (`track: device`, `track: cloud`,
  `track: ai`, `track: content`).
- **One pull request per issue.** Put `Closes #<n>` in the PR description so
  the issue closes when it merges.
- Issues are written to be independent. If you need something from another
  track, work against the contract written in the issue (MQTT topics, REST API)
  or a mock, not against unfinished code.

## Branch names

`<track>/<issue-number>-<short-name>`, for example:

```
device/4-irrigation-firmware
cloud/14-rest-api
ai/20-assistant
content/16-crop-calendar
```

## Repository layout

```
firmware/    PlatformIO projects, one per ESP32 node
hardware/    wiring diagrams, BOM, solar sizing
backend/     MQTT broker, database, ingest, API, alerts, weather rule
web/         dashboard PWA
site/        public landing page and crop calendar page (GitHub Pages)
assistant/   AI farming assistant (knowledge only)
agent/       farm agent (reads farm data, suggests, farmer approves)
ml/          prediction models
data/        crop calendar dataset
knowledge/   knowledge base notes for the assistant
docs/        architecture, progress log
```

## Running things locally

Each folder has a README with its own steps. The usual pattern:

| Part | Command |
|---|---|
| Firmware | `cd firmware/<node> && cp include/secrets.example.h include/secrets.h && pio run` |
| Backend stack | `cd backend && cp .env.example .env && docker compose up` |
| Python services | `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && pytest` |
| Web dashboard | `cd web && npm ci && npm run dev` |

## Secrets

Never commit passwords, tokens or API keys. Copy `.env.example` to `.env`
(or `secrets.example.h` to `secrets.h` for firmware) and fill in your own
values; both are ignored by git. If a secret is committed by mistake, rotate it
right away: removing it in a later commit does not remove it from history.

## Pull requests

- Keep PRs small and focused on one issue.
- Add or update tests when you change behaviour, and run them before pushing.
- Write commit messages in the imperative ("Add hive node firmware").
- Update the folder's README when you change how something is run.

## Licence

By contributing you agree that your code is released under the MIT licence and
documentation, data and images under CC BY 4.0, as described in [LICENSE](LICENSE).
