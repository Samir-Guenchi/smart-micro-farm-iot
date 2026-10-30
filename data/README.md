# Data

## `crop-calendar.json`

What to sow, plant, prune, prepare or harvest, by country and month. It feeds
the crop calendar page (`site/calendar/`) and the AI farming assistant.

It is a flat JSON array; each row is one action for one crop in one month:

```json
{"country": "LV", "crop": "potato", "month": 5, "action": "plant", "notes": "Plant once the soil is above 8 °C ..."}
```

| Field | Values |
|---|---|
| `country` | ISO 3166 code: `LV` Latvia, `DZ` Algeria, `FR` France, `SE` Sweden, `MA` Morocco |
| `crop` | Farm vegetables: `potato`, `lettuce`, `tomato`, `broad_bean`, `corn`, `mushroom`. Fruit trees: `pomegranate`, `apricot`, `lemon`, `orange`, `peach`, `mulberry`, `plum` |
| `month` | 1–12 |
| `action` | `sow`, `plant`, `harvest`, `prepare`, `prune` |
| `notes` | One or two plain-language sentences |

An action that spans several months is repeated once per month with the same
note, so filtering by month is a simple equality check. Every country has at
least one row in every month (winter months use `prepare` rows for planning,
storage checks and tree protection).

### Regions the dates assume

Each country covers very different climates, so the dates are for one region
and the notes say when another region differs.

| Country | Region the dates are for | Elsewhere |
|---|---|---|
| Latvia | Whole country (last frost mid to late May, first frost late September) | |
| Sweden | South (Skåne, Götaland) | 2–4 weeks later in the north |
| France | North (Île-de-France) | 2–4 weeks earlier in the south |
| Algeria | Coastal and sub-coastal plains (Mitidja) | High plateaus are later and colder |
| Morocco | Atlantic and Mediterranean plains (Gharb, Saïss, Souss) | The Atlas is later and colder |

Citrus, pomegranate and peach do not grow outdoors in Latvia and Sweden; their
rows there are about keeping them in pots or a greenhouse.

### Checking changes

```
python3 data/validate_crop_calendar.py
```

It checks the field names and allowed values, duplicate rows, and that every
country has every month covered. Run it before committing a change.

### Sources

Compiled from general growing guidance for each country, then simplified to
one region per country. These are the references to check rows against; the
dataset has not yet been verified row by row against each of them, and the
founder should review it against his own experience on the farm.

- FAO Crop Calendar, cropcalendar.apps.fao.org (all five countries)
- Latvia: Latvian Rural Advisory and Training Centre (LLKC), lauku.lv
- Sweden: Swedish Board of Agriculture (Jordbruksverket) and SLU Trädgård
- France: INRAE and the Société Nationale d'Horticulture de France (SNHF)
- Algeria: Institut Technique des Cultures Maraîchères et Industrielles (ITCMI)
  and Institut Technique de l'Arboriculture Fruitière et de la Vigne (ITAFV)
- Morocco: INRA Maroc and the Ministry of Agriculture's regional guides
- Fruit tree pruning times: Royal Horticultural Society (RHS) guidance on stone
  fruit and citrus

Licence: CC BY 4.0, see [LICENSE](../LICENSE).
