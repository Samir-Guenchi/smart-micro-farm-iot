"""Append-only decision log: every suggestion, decision and outcome, one JSON object per line."""
from __future__ import annotations

import json
import time
from pathlib import Path


class DecisionLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, kind: str, suggestion_id: str, **fields) -> dict:
        entry = {"ts": int(time.time()), "kind": kind, "suggestion_id": suggestion_id, **fields}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def entries(self, suggestion_id: str | None = None) -> list[dict]:
        if not self.path.exists():
            return []
        rows = [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return [r for r in rows if suggestion_id is None or r["suggestion_id"] == suggestion_id]

    def suggestion(self, suggestion_id: str) -> dict | None:
        rows = self.entries(suggestion_id)
        created = next((r for r in rows if r["kind"] == "suggested"), None)
        if created is None:
            return None
        decided = next((r for r in rows if r["kind"] == "decided"), None)
        return {**created, "decision": decided["decision"] if decided else None}
