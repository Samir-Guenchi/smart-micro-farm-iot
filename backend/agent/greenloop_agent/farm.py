"""Access to farm data: the real REST API, or a mock built from fixtures/week.json.

Both follow the shared API contract (see docs/architecture.md):
  GET  /api/nodes
  GET  /api/readings?node=&metric=&from=&to=
  GET  /api/events?node=&type=&limit=
  POST /api/nodes/<id>/pump   {"duration_s": 600}
plus a weather forecast from Open-Meteo.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "week.json"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
FORECAST_FIELDS = "precipitation_sum,precipitation_probability_max,temperature_2m_max,et0_fao_evapotranspiration"


def _get_json(url: str, headers: dict | None = None, timeout: float = 15):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


class FarmAPI:
    """Talks to the backend REST API (backend/api) with a bearer token."""

    def __init__(self, base_url: str, token: str, lat: float, lon: float):
        self.base = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        self.lat, self.lon = lat, lon

    def now(self) -> int:
        return int(time.time())

    def _get(self, path: str, **params):
        q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        return _get_json(f"{self.base}{path}" + (f"?{q}" if q else ""), self.headers)

    def list_nodes(self) -> list[dict]:
        return self._get("/nodes")

    def get_readings(self, node: str, metric: str, start: int, end: int) -> list[dict]:
        return self._get("/readings", node=node, metric=metric, **{"from": start, "to": end})

    def get_events(self, node: str | None = None, type: str | None = None, limit: int = 50) -> list[dict]:
        return self._get("/events", node=node, type=type, limit=limit)

    def pump(self, node: str, duration_s: int) -> dict:
        body = json.dumps({"duration_s": duration_s}).encode()
        req = urllib.request.Request(
            f"{self.base}/nodes/{urllib.parse.quote(node)}/pump",
            data=body,
            method="POST",
            headers={**self.headers, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return {"status": r.status, **json.loads(r.read() or b"{}")}

    def get_forecast(self) -> dict:
        q = urllib.parse.urlencode(
            {"latitude": self.lat, "longitude": self.lon, "daily": FORECAST_FIELDS, "forecast_days": 3, "timezone": "auto"}
        )
        return _get_json(f"{OPEN_METEO}?{q}")


class MockFarm:
    """Same interface as FarmAPI, backed by a week of fixture data. Pump calls are recorded, not sent."""

    def __init__(self, path: Path = FIXTURE):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self._now = data["now"]
        self.nodes = data["nodes"]
        self.readings = data["readings"]
        self.events = data["events"]
        self.forecast = data["forecast"]
        self.pump_calls: list[dict] = []

    def now(self) -> int:
        return self._now

    def list_nodes(self):
        return self.nodes

    def get_readings(self, node, metric, start, end):
        return [p for p in self.readings.get(f"{node}|{metric}", []) if start <= p["ts"] <= end]

    def get_events(self, node=None, type=None, limit=50):
        rows = [e for e in self.events if (node is None or e["node"] == node) and (type is None or e["type"] == type)]
        return sorted(rows, key=lambda e: e["ts"], reverse=True)[:limit]

    def pump(self, node, duration_s):
        self.pump_calls.append({"node": node, "duration_s": duration_s})
        return {"status": 202, "ok": True}

    def get_forecast(self):
        return self.forecast
