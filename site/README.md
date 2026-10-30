# Public site

A one-page site for customers and visitors, published on GitHub Pages:
the loop, produce, farm visits, photos and contact. No build step and no
framework: `index.html`, `style.css`, `site.js`, and photos in `img/`
(resized copies of `assets/images/`).

## Shop and bookings: ready-made tools, set in `config.js`

| Setting | Empty (default) | Set |
|---|---|---|
| `shopUrl` | An order form that sends the order as a message | A button to the shop (Shopify Starter, WooCommerce, Square…) |
| `calLink` | A visit request form | A Cal.com booking calendar embedded inline, e.g. `"greenloop/farm-tour"` |
| `whatsapp` / `email` | Forms can't send; a "contact us directly" note shows | Forms open WhatsApp or the email app with the message filled in |

**Before launch, set at least `whatsapp` or `email`.** Cal.com is free: create
an account, add event types (tour, harvest day, meal, school visit) and put
the link in `calLink`.

## Preview locally

```bash
./site/build.sh && python3 -m http.server -d site/_site 8000
# open http://localhost:8000
```

## Publish

The `pages` workflow deploys on every push to `main` that touches `site/` or
`data/`. One-time setup: **Settings → Pages → Build and deployment → Source:
GitHub Actions**. The site is then at
`https://samir-guenchi.github.io/smart-micro-farm-iot/`.
