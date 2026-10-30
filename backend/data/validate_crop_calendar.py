"""Check backend/data/crop-calendar.json against the schema in backend/data/README.md.

Run from the repo root: python3 backend/data/validate_crop_calendar.py
Exits non-zero and lists the problems if anything is wrong.
"""
import json
import pathlib
import sys

COUNTRIES = {"LV", "DZ", "FR", "SE", "MA"}
ACTIONS = {"sow", "plant", "harvest", "prepare", "prune"}
CROPS = {
    # vegetables grown on the farm
    "potato", "lettuce", "tomato", "broad_bean", "corn", "mushroom",
    # perimeter fruit trees
    "pomegranate", "apricot", "lemon", "orange", "peach", "mulberry", "plum",
}
KEYS = {"country", "crop", "month", "action", "notes"}


def validate(rows):
    errors = []
    if not isinstance(rows, list):
        return ["top level must be a JSON array"]
    seen = set()
    months = {c: set() for c in COUNTRIES}
    for i, r in enumerate(rows):
        where = f"row {i}"
        if not isinstance(r, dict) or set(r) != KEYS:
            errors.append(f"{where}: keys must be exactly {sorted(KEYS)}")
            continue
        if r["country"] not in COUNTRIES:
            errors.append(f"{where}: unknown country {r['country']!r}")
        if r["crop"] not in CROPS:
            errors.append(f"{where}: unknown crop {r['crop']!r} (add it to CROPS if it is new)")
        if r["action"] not in ACTIONS:
            errors.append(f"{where}: unknown action {r['action']!r}")
        if not isinstance(r["month"], int) or not 1 <= r["month"] <= 12:
            errors.append(f"{where}: month must be an integer 1-12")
        if not isinstance(r["notes"], str) or not r["notes"].strip():
            errors.append(f"{where}: notes must be a non-empty string")
        key = (r["country"], r["crop"], r["month"], r["action"])
        if key in seen:
            errors.append(f"{where}: duplicate {key}")
        seen.add(key)
        if r["country"] in months and isinstance(r["month"], int):
            months[r["country"]].add(r["month"])
    for c, ms in sorted(months.items()):
        missing = sorted(set(range(1, 13)) - ms)
        if missing:
            errors.append(f"{c}: no rows for months {missing}")
    return errors


def main():
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "backend/data/crop-calendar.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    errors = validate(rows)
    for e in errors:
        print(e)
    if errors:
        sys.exit(1)
    print(f"{path}: {len(rows)} rows OK")


if __name__ == "__main__":
    main()
