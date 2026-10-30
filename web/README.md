# Farm dashboard (PWA)

The custom GreenLoop dashboard: React + TypeScript + Vite, installable on a
phone as a Progressive Web App.

| Page | What's on it |
|---|---|
| **Farm** | One card per node: live values, online/offline, last seen |
| **Bed** | Pump on/off, **Water now** button with a 5/10/15 min picker (confirm first), soil moisture history for 6 h / 24 h / 3 days |
| **Coop** | Door state and today's open/close times |
| **Settings** | Language, push notifications, install button, sign out |

Data refreshes every 30 s while the app is open (15 s for the pump state).

## Run

```bash
cd web
npm install
npm run dev            # http://localhost:5173
```

With no `VITE_API_BASE` set, the app uses a **built-in mock** of the API
(`src/mock/server.ts`) and any username/password signs in. A "Demo mode" banner
shows when the mock is on.

To use the real API (`backend/api`), set one base URL:

```bash
cp .env.example .env.local     # VITE_API_BASE=http://localhost:8000
npm run dev
```

and add the dashboard's origin to the API's `CORS_ORIGINS`.

## Build and deploy

```bash
npm run build          # static files in dist/
npm run preview        # serve dist/ locally
```

`dist/` is plain static files with relative paths, so it can be served by nginx
or Caddy on the VPS next to the API, or from any static host. Service workers
need HTTPS (localhost is fine for testing).

## PWA

- `manifest.webmanifest` with the GreenLoop icons (generated from
  `assets/brand/greenloop-mark.png` into `public/icons/`), standalone display
  and brand colours.
- Service worker (`src/sw.ts`): precaches the app shell so it opens without a
  connection, and shows push notifications (tapping one opens the right page).
- **Install:** Android/Chrome shows an Install button in Settings; on iPhone use
  Share → Add to Home Screen.
- **Push:** set `VITE_VAPID_PUBLIC_KEY`, and "Enable notifications" subscribes
  the device and sends the subscription to `POST /api/push/subscribe`. The
  backend side (storing subscriptions and sending alerts with the VAPID private
  key) is not built yet; until then alerts come through Telegram.

## Translations and right-to-left

All text is in `src/locales/`: English (`en.json`), French (`fr.json`) and
Arabic (`ar.json`); components never contain English strings. Arabic uses all
six plural forms (`_zero`, `_one`, `_two`, `_few`, `_many`, `_other`), French
`_one`, `_many` and `_other`. When you add a key to `en.json`, add it to the
other files too: `src/locales.test.ts` fails if a key or placeholder is
missing. A new language is a new locale file plus one line in `src/i18n.ts`.
The `<html dir>` switches to `rtl` for Arabic, and the CSS uses logical
properties (`margin-inline-start`, `inset-inline`…), so the layout mirrors
without extra styles. Try it with `?lang=ar`.

## Tests

```bash
npm test               # vitest + Testing Library, against the mock API
npm run typecheck
```
