# Progress log

One short entry per month: what was installed, what data came in, users and
sales, and what is next. It is the raw material for the yearly residence
permit renewal report (see the checkpoints in [ROADMAP.md](../ROADMAP.md)), so
write facts and numbers, link to pull requests and photos, and keep each
entry to what a reviewer needs.

Add the newest month at the top. Copy the template at the bottom.

---

## October – November 2026

*Covers the start of the project up to 30 October 2026. November items to be
added at the end of the month.*

**On the farm**
- Installed and working: Okköbi automatic coop door (light-sensor schedule,
  manual override) and a solar-powered security camera with night vision
  covering the poultry area, orchard entrance and irrigation zones.
- Three ESP32 boards bought and being programmed for the irrigation, hive and
  coop nodes.

**Software and docs (this repository)**
- New logo and README (PRs #1, #2); phased build plan in `ROADMAP.md` (#3).
- Work organised as 23 issues across four tracks (device, cloud, AI, content),
  split between two developers.
- Cloud backend: MQTT broker, TimescaleDB, Grafana "Farm overview", data
  simulator (#27); Telegram alerts for dry beds, open coop door, offline nodes
  and long pump runs (#28); REST API with login and pump control (#29);
  weather-aware irrigation that skips watering before rain (#33).
- Web: farm dashboard as an installable PWA with English locale and
  right-to-left support (#30); public landing page with shop and visit
  booking links (#31); crop calendar page (#32).
- Content: crop calendar dataset for Latvia, Algeria, France, Sweden and
  Morocco, 403 rows (#36); knowledge base with 32 draft farming notes (#37);
  license, contributing guide and issue templates (#35); this architecture
  doc and progress log (#12).
- AI: farming assistant prototype answering from the knowledge base with
  citations (#38); farm agent v1 that suggests watering and waits for the
  farmer's approval on Telegram (#39); soil-drying prediction model trained on
  simulated data (#40).
- Firmware and hardware docs for the three nodes: in review (#34).

**Data collected:** none from the field yet; everything so far runs on
simulated data.

**Users and sales:** none yet.

**Company and programs:** *(founder to fill in: company registration, LIAA /
Venture Catalysts status)*

**Next month**
- Merge the firmware, flash the three nodes and install the irrigation node in
  a bed: first real soil readings in Grafana and a first real Telegram alert.
- Deploy the backend on a server and point the dashboard at it.
- Founder reviews the knowledge base notes and crop calendar rows.
- Fill in the shop and booking links on the landing page and publish it.

---

## Template

```markdown
## <Month> <Year>

**On the farm** – what was installed, planted, harvested, built.
**Software and docs** – what shipped, with PR links.
**Data collected** – e.g. "31 days of soil readings from bed 1, 1,240 L of water logged".
**Users and sales** – assistant users, orders, visits, revenue.
**Company and programs** – registration, grants, accelerators, partners.
**Problems** – what went wrong and what was done about it.
**Next month** – the three most important things.
```
