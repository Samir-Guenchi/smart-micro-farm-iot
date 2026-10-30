# Knowledge base

Short, practical farming notes that the AI farming assistant (`assistant/`)
searches to answer questions. One topic per file, in plain language.

## Writing a note

1. Copy [`_template.md`](_template.md) to a new file named after the topic in
   lowercase with dashes, for example `tomato-late-blight.md`.
2. Fill in the front matter:
   - `title`: what a farmer would call the topic.
   - `crops`: crop ids from [`data/README.md`](../data/README.md), or `[]` for
     animals and general topics.
   - `countries`: `[all]` or a list of `LV`, `DZ`, `FR`, `SE`, `MA`.
   - `season`: when the note applies.
   - `source`: where the advice comes from.
   - `reviewed`: `true` once the founder has checked it.
3. Keep it short: what it looks like, why, what to do.

Files starting with `_` and this README are not indexed by the assistant.

## Status

The first 32 notes were drafted from general extension guidance (FAO, RHS and
national advisory services) so the assistant has something to work with. They
all have `reviewed: false`: the founder should read each one, correct it from
his own experience on the farm, and set `reviewed: true`.

| Topic | Notes |
|---|---|
| Diseases and pests | tomato-late-blight, tomato-blossom-end-rot, tomato-early-blight, potato-colorado-beetle, lettuce-aphids, slugs-in-vegetable-beds, lettuce-bolting, broad-bean-black-aphid, broad-bean-chocolate-spot, corn-pests-and-smut, mushroom-contamination, peach-leaf-curl, citrus-pests, stone-fruit-brown-rot |
| Soil and compost | composting-poultry-manure, hot-compost-method, crop-rotation |
| Irrigation | drip-irrigation-schedule, soil-moisture-thresholds, pond-water-fertigation |
| Planting | companion-planting, three-sisters, fruit-tree-pruning |
| Poultry and quail | laying-hens-daily-care, quail-care, poultry-winter-care, poultry-red-mite |
| Bees | beekeeping-calendar, varroa-treatment, swarm-prevention |
| Pond and other animals | azolla, snail-farming-basics |

Licence: CC BY 4.0, see [LICENSE](../LICENSE).
