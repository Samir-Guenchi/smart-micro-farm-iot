import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from weather import Config, DecisionLog, command_for, decide  # noqa: E402

NOW = 1_800_000_000 - (1_800_000_000 % 3600) + 1800  # half past an hour
CFG = Config(latitude=56.95, longitude=24.11)


def forecast(rain_by_hour, prob=80, start=NOW - 1800, hours=72):
    """Open-Meteo shaped response; rain_by_hour maps hours-from-now to mm."""
    times = [start + h * 3600 for h in range(hours)]
    return {
        "hourly": {
            "time": times,
            "precipitation": [rain_by_hour.get(h, 0.0) for h in range(hours)],
            "precipitation_probability": [prob if rain_by_hour.get(h) else 5 for h in range(hours)],
        }
    }


def test_dry_forecast_waters_as_usual():
    d = decide(forecast({}), NOW, CFG)
    assert not d.skip and d.until == NOW and d.rain_mm == 0
    assert command_for(d, None) is None


def test_heavy_likely_rain_skips_for_the_window():
    d = decide(forecast({3: 2.0, 4: 3.5, 5: 1.0}), NOW, CFG)
    assert d.skip and d.rain_mm == 6.5 and d.max_probability == 80
    assert d.until == NOW + 24 * 3600
    assert command_for(d, None) == {"action": "skip_auto_water", "until": NOW + 24 * 3600}


def test_rain_late_in_window_extends_skip_past_it():
    d = decide(forecast({22: 6.0}), NOW, CFG)
    rain_hour_start = NOW - 1800 + 22 * 3600
    assert d.skip and d.until == rain_hour_start + 7 * 3600


def test_light_rain_does_not_skip():
    d = decide(forecast({2: 1.0, 3: 2.0}), NOW, CFG)
    assert not d.skip and "threshold" in d.reason


def test_unlikely_rain_does_not_skip():
    d = decide(forecast({2: 10.0}, prob=30), NOW, CFG)
    assert not d.skip and "chance" in d.reason


def test_rain_beyond_the_window_is_ignored():
    assert not decide(forecast({30: 20.0}), NOW, CFG).skip


def test_past_hours_are_ignored_but_current_hour_counts():
    f = forecast({0: 6.0}, start=NOW - 1800 - 3 * 3600)  # rain 3 h ago
    assert not decide(f, NOW, CFG).skip
    f = forecast({0: 6.0})  # rain in the hour that is in progress
    assert decide(f, NOW, CFG).skip


def test_missing_probability_falls_back_to_amount():
    f = forecast({2: 6.0})
    f["hourly"]["precipitation_probability"] = [None] * 72
    assert decide(f, NOW, CFG).skip


def test_cancelling_an_active_skip_when_rain_disappears():
    skip = decide(forecast({3: 8.0}), NOW, CFG)
    later = decide(forecast({}, start=NOW + 3 * 3600 - 1800), NOW + 3 * 3600, CFG)
    assert command_for(later, skip) == {"action": "skip_auto_water", "until": NOW + 3 * 3600}
    # Once the earlier skip has expired there is nothing to cancel.
    much_later = decide(forecast({}, start=NOW + 30 * 3600 - 1800), NOW + 30 * 3600, CFG)
    assert command_for(much_later, skip) is None


def test_decisions_are_logged_as_json_lines(tmp_path):
    path = tmp_path / "decisions.jsonl"
    log = DecisionLog(str(path))
    log.write(decide(forecast({3: 8.0}), NOW, CFG), "irrigation-1")
    log.write(decide(forecast({}), NOW + 3600, CFG), "irrigation-1")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["skip"] for r in rows] == [True, False]
    assert {"date", "node", "rain_mm", "max_probability", "until", "reason"} <= set(rows[0])
