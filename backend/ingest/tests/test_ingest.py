import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingest import parse  # noqa: E402


def test_telemetry_becomes_one_row_per_metric():
    payload = json.dumps({"ts": 1767225600, "metrics": {"soil_moisture_pct": 41.2, "air_temp_c": 18.5}}).encode()
    rows = parse("greenloop/irrigation-1/telemetry", payload)
    telemetry = [r for t, r in rows if t == "telemetry"]
    assert {(r["metric"], r["value"]) for r in telemetry} == {("soil_moisture_pct", 41.2), ("air_temp_c", 18.5)}
    assert all(r["node"] == "irrigation-1" and r["ts"].timestamp() == 1767225600 for r in telemetry)
    assert ("node_status", {"node": "irrigation-1", "status": "online", "last_seen": telemetry[0]["ts"]}) in rows


def test_status_accepts_plain_and_quoted_strings():
    assert parse("greenloop/coop-1/status", b"offline")[0][1]["status"] == "offline"
    assert parse("greenloop/coop-1/status", b'"online"')[0][1]["status"] == "online"
    assert parse("greenloop/coop-1/status", b"sleepy") == []


def test_event_keeps_extra_fields():
    payload = json.dumps({"ts": 1767225600, "type": "pump", "state": "stopped", "reason": "timeout", "liters": 12}).encode()
    table, row = parse("greenloop/irrigation-1/event", payload)[0]
    assert table == "events"
    assert (row["type"], row["state"], row["reason"]) == ("pump", "stopped", "timeout")
    assert json.loads(row["data"]) == {"liters": 12}


def test_garbage_is_ignored():
    assert parse("greenloop/irrigation-1/telemetry", b"not json") == []
    assert parse("other/irrigation-1/telemetry", b"{}") == []
    assert parse("greenloop/irrigation-1/cmd", b'{"action": "pump"}') == []
    assert parse("greenloop/irrigation-1/event", b'{"ts": 1}') == []
