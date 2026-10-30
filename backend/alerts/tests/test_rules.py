import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rules import Config, Rules  # noqa: E402
from sun import sun_times  # noqa: E402

RIGA = dict(latitude=56.95, longitude=24.11)
NOON = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)  # midday in Riga


def minutes(n):
    return timedelta(minutes=n)


def make(now=NOON, **kw):
    return Rules(Config(**RIGA, **kw), now)


def keys(alerts, resolved=False):
    return [a.key for a in alerts if a.resolved == resolved]


def test_sunset_in_riga_matches_almanac():
    # Riga, 21 June: sunset about 22:22 local (19:22 UTC), sunrise about 04:29 local (01:29 UTC).
    rise, set_ = sun_times(date(2026, 6, 21), 56.95, 24.11)
    assert abs((set_ - datetime(2026, 6, 21, 19, 22, tzinfo=timezone.utc)).total_seconds()) < 5 * 60
    assert abs((rise - datetime(2026, 6, 21, 1, 29, tzinfo=timezone.utc)).total_seconds()) < 5 * 60


def test_dry_bed_needs_30_minutes_and_fires_once():
    r = make()
    online = lambda t: [r.on_telemetry(n, {}, t) for n in ("hive-1", "coop-1")]  # noqa: E731
    for i in range(0, 29):
        t = NOON + minutes(i)
        online(t)
        r.on_telemetry("irrigation-1", {"soil_moisture_pct": 20}, t)
        assert r.tick(t) == []
    sent = []
    for i in range(30, 60):
        t = NOON + minutes(i)
        online(t)
        r.on_telemetry("irrigation-1", {"soil_moisture_pct": 20}, t)
        sent += r.tick(t)
    assert keys(sent) == ["dry:irrigation-1"]


def test_dry_bed_clears_with_hysteresis():
    r = make()
    r.on_telemetry("irrigation-1", {"soil_moisture_pct": 20}, NOON)
    t = NOON + minutes(31)
    r.on_telemetry("irrigation-1", {"soil_moisture_pct": 20}, t)
    assert "dry:irrigation-1" in keys(r.tick(t))
    r.on_telemetry("irrigation-1", {"soil_moisture_pct": 26}, t)  # just above threshold: still active
    assert "dry:irrigation-1" not in keys(r.tick(t), resolved=True)
    r.on_telemetry("irrigation-1", {"soil_moisture_pct": 40}, t)
    assert "dry:irrigation-1" in keys(r.tick(t), resolved=True)


def test_dry_reading_interrupted_resets_the_timer():
    r = make()
    r.on_telemetry("irrigation-1", {"soil_moisture_pct": 20}, NOON)
    r.on_telemetry("irrigation-1", {"soil_moisture_pct": 30}, NOON + minutes(20))
    r.on_telemetry("irrigation-1", {"soil_moisture_pct": 20}, NOON + minutes(25))
    assert "dry:irrigation-1" not in keys(r.tick(NOON + minutes(40)))


def test_node_offline_by_status_and_by_silence():
    r = make()
    for n in ("irrigation-1", "hive-1", "coop-1"):
        r.on_telemetry(n, {}, NOON)
    r.on_status("coop-1", "offline", NOON + minutes(1))
    assert keys(r.tick(NOON + minutes(1))) == ["offline:coop-1"]
    r.on_telemetry("irrigation-1", {}, NOON + minutes(9))
    later = keys(r.tick(NOON + minutes(11)))
    assert later == ["offline:hive-1"]  # irrigation-1 reported recently, coop-1 already alerted
    r.on_status("coop-1", "online", NOON + minutes(12))
    assert "offline:coop-1" in keys(r.tick(NOON + minutes(12)), resolved=True)


def test_door_open_after_sunset_alerts_and_clears_on_close():
    r = make(nodes=[])
    _, sunset = sun_times(NOON.date(), 56.95, 24.11)
    r.on_event("coop-1", {"type": "door", "state": "open"}, NOON)
    assert r.tick(sunset + minutes(10)) == []
    assert keys(r.tick(sunset + minutes(31))) == ["door"]
    assert r.tick(sunset + minutes(60)) == []
    r.on_event("coop-1", {"type": "door", "state": "closed"}, sunset + minutes(61))
    assert keys(r.tick(sunset + minutes(61)), resolved=True) == ["door"]


def test_door_alert_still_works_after_midnight_utc():
    r = make(nodes=[])
    r.on_event("coop-1", {"type": "door", "state": "open"}, NOON)
    just_after_midnight = datetime(2026, 6, 2, 0, 10, tzinfo=timezone.utc)  # still night in Riga
    assert keys(r.tick(just_after_midnight)) == ["door"]


def test_unknown_door_state_does_not_alert():
    r = make(nodes=[])
    _, sunset = sun_times(NOON.date(), 56.95, 24.11)
    assert r.tick(sunset + minutes(45)) == []


def test_pump_running_longer_than_requested():
    r = make(nodes=[])
    r.on_event("irrigation-1", {"type": "pump", "state": "started", "duration_s": 600}, NOON)
    assert r.tick(NOON + minutes(11)) == []
    assert keys(r.tick(NOON + minutes(13))) == ["pump:irrigation-1"]
    r.on_event("irrigation-1", {"type": "pump", "state": "stopped"}, NOON + minutes(14))
    assert keys(r.tick(NOON + minutes(14)), resolved=True) == ["pump:irrigation-1"]


def test_pump_without_duration_uses_max_from_telemetry():
    r = make(nodes=[])
    r.on_telemetry("irrigation-1", {"pump_on": 1}, NOON)
    r.on_telemetry("irrigation-1", {"pump_on": 1}, NOON + minutes(10))  # does not restart the clock
    assert r.tick(NOON + minutes(21)) == []
    assert keys(r.tick(NOON + minutes(23))) == ["pump:irrigation-1"]


def test_config_from_toml_file():
    import tomllib

    path = Path(__file__).resolve().parents[1] / "config.example.toml"
    cfg = Config.from_toml(tomllib.loads(path.read_text()))
    assert cfg.dry_minutes == 30 and cfg.offline_minutes == 10 and cfg.door_minutes_after_sunset == 30
