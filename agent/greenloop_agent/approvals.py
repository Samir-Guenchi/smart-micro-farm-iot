"""Suggest-and-approve: turn a farmer's Approve tap into a pump command, and log everything.

A suggestion only reaches the pump through `Approvals.decide(..., "approve")`, which
re-checks the safety rules, refuses stale or already-decided suggestions, and logs
the decision and the outcome.
"""
from __future__ import annotations

import time

from .log import DecisionLog
from .tools import MAX_PUMP_S, Suggestion

EXPIRES_S = 12 * 3600  # advice based on this morning's data is stale by tonight


class Approvals:
    def __init__(self, farm, log: DecisionLog, clock=time.time):
        self.farm = farm
        self.log = log
        self.clock = clock

    def record(self, s: Suggestion, report: str = "") -> None:
        self.log.write("suggested", s.id, created=int(self.clock()), **{k: v for k, v in s.to_dict().items() if k != "id"}, report=report)

    def decide(self, suggestion_id: str, decision: str, by: str) -> str:
        """Apply the farmer's decision. Returns a short message to show the farmer."""
        if decision not in ("approve", "reject"):
            raise ValueError("decision must be approve or reject")
        s = self.log.suggestion(suggestion_id)
        if s is None:
            return "I can't find that suggestion."
        if s["decision"] is not None:
            past = {"approve": "approved", "reject": "rejected", "expire": "expired"}
            return f"Already {past.get(s['decision'], s['decision'])}."
        if self.clock() - s["created"] > EXPIRES_S:
            self.log.write("decided", suggestion_id, decision="expire", by=by)
            return "This suggestion expired; the next check will look again with fresh data."
        self.log.write("decided", suggestion_id, decision=decision, by=by)
        if decision == "reject":
            return "Rejected. Nothing was changed."
        # Re-check the rules at the moment of acting, whatever the log says.
        if s["action"] != "water" or not s["node"].startswith("irrigation-") or not 0 < s["duration_s"] <= MAX_PUMP_S:
            self.log.write("outcome", suggestion_id, ok=False, error="blocked by safety rules")
            return "Blocked: this action is not allowed for the agent."
        try:
            result = self.farm.pump(s["node"], s["duration_s"])
        except Exception as e:
            self.log.write("outcome", suggestion_id, ok=False, error=str(e))
            return f"Approved, but the pump command failed: {e}"
        self.log.write("outcome", suggestion_id, ok=True, result=result)
        return f"Approved. Watering {s['node']} for {s['duration_s'] // 60} min."
