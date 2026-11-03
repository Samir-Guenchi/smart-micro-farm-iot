import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from risks import Notified, RiskConfig, detect  # noqa: E402

# 2027-07-01 00:00 UTC; the farm is in Algeria (UTC+1).
MIDNIGHT = 1_814_400_000
NOW = MIDNIGHT + 6 * 3600
CFG = RiskConfig()


def forecast(temp=25.0, rh=50.0, wind=10.0, gust=20.0, hours=72, offset=3600, **at):
    """Hourly forecast starting at MIDNIGHT. `at` overrides single hours: t12=40, rh12=10, w12=35, g12=70."""
    series = {"t": [temp] * hours, "rh": [rh] * hours, "w": [wind] * hours, "g": [gust] * hours}
    for key, value in at.items():
        name, hour = key.rstrip("0123456789"), int(key.lstrip("rhtwg"))
        series[name][hour] = value
    return {
        "utc_offset_seconds": offset,
        "hourly": {
            "time": [MIDNIGHT + h * 3600 for h in range(hours)],
            "temperature_2m": series["t"],
            "relative_humidity_2m": series["rh"],
            "wind_speed_10m": series["w"],
            "wind_gusts_10m": series["g"],
        },
    }


def test_mild_weather_has_no_risk():
    assert detect(forecast(), NOW, CFG) == []


def test_heat_wave_reports_peak_and_hours():
    f = forecast(t12=38.5, t13=41.0, t14=39.0)
    [risk] = detect(f, NOW, CFG)
    assert risk.kind == "heat" and risk.peak == 41.0 and risk.hours == 3
    assert risk.start == MIDNIGHT + 12 * 3600 and risk.peak_ts == MIDNIGHT + 13 * 3600
    assert risk.day == "2027-07-01"


def test_sirocco_needs_heat_dryness_and_wind_in_the_same_hour():
    hot_dry_calm = forecast(t13=36, rh13=15)
    assert [r.kind for r in detect(hot_dry_calm, NOW, CFG)] == []
    sirocco = forecast(t13=36, rh13=15, w13=40)
    assert [r.kind for r in detect(sirocco, NOW, CFG)] == ["sirocco"]


def test_frost_reports_the_lowest_temperature():
    f = forecast(t28=1.5, t29=-0.5, t30=0.8)
    [risk] = detect(f, NOW, CFG)
    assert risk.kind == "frost" and risk.peak == -0.5 and risk.day == "2027-07-02"


def test_strong_gusts():
    assert [r.kind for r in detect(forecast(g20=75), NOW, CFG)] == ["wind"]


def test_one_risk_per_kind_per_local_day():
    # 23:00 UTC is already the next day at UTC+1.
    f = forecast(t15=40, t23=39)
    risks = detect(f, NOW, CFG)
    assert [(r.kind, r.day) for r in risks] == [("heat", "2027-07-01"), ("heat", "2027-07-02")]


def test_past_hours_and_hours_after_the_window_are_ignored():
    f = forecast(t2=45, t60=45)
    assert detect(f, NOW, CFG) == []


def test_event_payload():
    [risk] = detect(forecast(t12=40), NOW, CFG)
    event = risk.event()
    assert event["type"] == "weather_risk" and event["state"] == "heat"
    assert event["day"] == "2027-07-01" and event["peak"] == 40.0


def test_notified_only_returns_new_risks():
    n = Notified()
    risks = detect(forecast(t12=40), NOW, CFG)
    assert len(n.new(risks)) == 1
    assert n.new(risks) == []
    assert len(n.new(detect(forecast(t12=40, t30=1), NOW, CFG))) == 1  # frost is new


def test_thresholds_from_env(monkeypatch):
    monkeypatch.setenv("HEAT_C", "32")
    assert RiskConfig.from_env().heat_c == 32
    assert [r.kind for r in detect(forecast(t12=33), NOW, RiskConfig.from_env())] == ["heat"]
