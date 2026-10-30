"""Tools the agent can call. Read tools query the farm; `suggest_watering` only records a proposal.

Safety rules live here in code, not only in the prompt:
- The agent has no tool that acts. A suggestion becomes a pump command only after the
  farmer taps Approve (see approvals.py).
- Only irrigation nodes can be suggested, for at most MAX_PUMP_S seconds.
- There is no tool for the coop door or anything involving animals.
"""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import asdict, dataclass

MAX_PUMP_S = 900  # same cap as the backend API and firmware
METRICS = ["soil_moisture_pct", "air_temp_c", "air_humidity_pct", "pump_on", "water_liters", "hive_weight_kg", "hive_temp_c", "battery_v"]
MAX_POINTS = 48

TOOLS = [
    {
        "name": "list_nodes",
        "description": "List every farm node with online/offline status, last-seen time and latest readings. Node ids: irrigation-N is bed N, hive-N a beehive, coop-1 the chicken coop door.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_readings",
        "description": "Get one metric from one node over the last N hours. Returns summary statistics (min, max, avg, first, last, sum) and up to 48 evenly spaced points with ISO times. For water use, read water_liters and use sum.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node id, e.g. irrigation-1"},
                "metric": {"type": "string", "enum": METRICS},
                "hours": {"type": "integer", "minimum": 1, "maximum": 720, "description": "How many hours back from now"},
            },
            "required": ["node", "metric", "hours"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_events",
        "description": "Get the most recent events, newest first: door open/closed, pump started/stopped (with reason), motion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Node id, or omit for all nodes"},
                "type": {"type": "string", "enum": ["door", "pump", "motion"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_forecast",
        "description": "Weather forecast for the farm for the next 3 days: rain (mm), rain probability (%), max temperature, and evapotranspiration (mm of water the crops lose).",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "suggest_watering",
        "description": "Propose watering one bed. This does NOT start the pump: the farmer gets the suggestion with your reason and decides. Use it only when the data clearly supports it, at most once per bed per check.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "An irrigation node id, e.g. irrigation-2"},
                "duration_min": {"type": "integer", "minimum": 1, "maximum": MAX_PUMP_S // 60},
                "when": {"type": "string", "description": "When to water, in plain words, e.g. 'tonight' or 'now'"},
                "reason": {"type": "string", "description": "One or two sentences citing the readings and forecast behind the suggestion"},
            },
            "required": ["node", "duration_min", "when", "reason"],
            "additionalProperties": False,
        },
    },
]


@dataclass
class Suggestion:
    id: str
    action: str
    node: str
    duration_s: int
    when: str
    reason: str

    def to_dict(self):
        return asdict(self)


class ToolError(Exception):
    pass


def _iso(ts: int) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def summarize(points: list[dict]) -> dict:
    if not points:
        return {"count": 0, "note": "no readings in this period"}
    values = [p["value"] for p in points]
    step = max(1, len(points) // MAX_POINTS)
    return {
        "count": len(points),
        "min": min(values),
        "max": max(values),
        "avg": round(sum(values) / len(values), 2),
        "sum": round(sum(values), 2),
        "first": {"time": _iso(points[0]["ts"]), "value": points[0]["value"]},
        "last": {"time": _iso(points[-1]["ts"]), "value": points[-1]["value"]},
        "points": [{"time": _iso(p["ts"]), "value": p["value"]} for p in points[::step][:MAX_POINTS]],
    }


class Toolbox:
    def __init__(self, farm, allow_suggestions: bool = True):
        self.farm = farm
        self.allow_suggestions = allow_suggestions
        self.suggestions: list[Suggestion] = []

    @property
    def definitions(self) -> list[dict]:
        return [t for t in TOOLS if self.allow_suggestions or t["name"] != "suggest_watering"]

    def run(self, name: str, args: dict):
        if name == "list_nodes":
            nodes = self.farm.list_nodes()
            return {"now": _iso(self.farm.now()), "nodes": [{**n, "last_seen": _iso(n["last_seen"])} for n in nodes]}
        if name == "get_readings":
            end = self.farm.now()
            start = end - int(args["hours"]) * 3600
            return summarize(self.farm.get_readings(args["node"], args["metric"], start, end))
        if name == "get_events":
            rows = self.farm.get_events(args.get("node"), args.get("type"), int(args.get("limit", 50)))
            return [{**e, "ts": _iso(e["ts"])} for e in rows]
        if name == "get_forecast":
            return self.farm.get_forecast()
        if name == "suggest_watering" and self.allow_suggestions:
            return self._suggest(args)
        raise ToolError(f"unknown tool {name}")

    def _suggest(self, args: dict) -> dict:
        node = str(args["node"])
        if not node.startswith("irrigation-"):
            raise ToolError("Only irrigation beds can be watered. The coop door and anything involving animals are never actioned by the agent.")
        known = {n["id"] for n in self.farm.list_nodes()}
        if node not in known:
            raise ToolError(f"Unknown node {node}. Known nodes: {sorted(known)}")
        if any(s.node == node for s in self.suggestions):
            raise ToolError(f"There is already a suggestion for {node} in this check.")
        duration_s = int(args["duration_min"]) * 60
        if not 60 <= duration_s <= MAX_PUMP_S:
            raise ToolError(f"duration_min must be between 1 and {MAX_PUMP_S // 60}")
        s = Suggestion(uuid.uuid4().hex[:10], "water", node, duration_s, str(args["when"]), str(args["reason"]))
        self.suggestions.append(s)
        return {"recorded": True, "suggestion_id": s.id, "note": "The farmer will be asked to approve or reject."}
