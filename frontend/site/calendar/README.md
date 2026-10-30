# Crop calendar page

A static page: pick a country, a month and optionally a crop, and see what to
sow, plant, prune, harvest or prepare, grouped by action. Mobile-first, no
build step. The filters are kept in the URL (`?country=LV&month=5`), so a view
can be shared.

**Data:** reads `data/crop-calendar.json` (issue #16) and falls back to
`sample.json` (10 illustrative rows) until that file is published. Row schema:

```json
{"country": "LV", "crop": "potato", "month": 4, "action": "plant", "notes": "..."}
```

Countries known to the page: `LV`, `DZ`, `FR`, `SE`, `MA` (others show by
their code). Crop ids like `broad_bean` are shown as "Broad bean".

**Preview:** from the repo root, `python3 -m http.server`, then open
<http://localhost:8000/site/calendar/>. On GitHub Pages it is served at
`/calendar/`, with `backend/data/` copied next to it as `data/` by `build.sh`.
