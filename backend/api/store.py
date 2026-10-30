"""Read access to the farm database (schema owned by backend/db/init.sql)."""

from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row


def _unix(dt):
    return int(dt.timestamp()) if dt else None


def _dt(unix):
    return datetime.fromtimestamp(unix, tz=timezone.utc)


class PostgresStore:
    def __init__(self, url):
        self.url = url

    def _query(self, sql, params=()):
        with psycopg.connect(self.url, row_factory=dict_row) as conn:
            return conn.execute(sql, params).fetchall()

    def nodes(self):
        status = self._query("SELECT node, status, last_seen FROM node_status ORDER BY node")
        latest = self._query(
            "SELECT DISTINCT ON (node, metric) node, metric, value FROM telemetry "
            "WHERE ts > now() - interval '1 day' ORDER BY node, metric, ts DESC"
        )
        by_node = {}
        for row in latest:
            by_node.setdefault(row["node"], {})[row["metric"]] = row["value"]
        return [
            {"id": r["node"], "status": r["status"], "last_seen": _unix(r["last_seen"]), "latest": by_node.get(r["node"], {})}
            for r in status
        ]

    def readings(self, node, metric, start, end, limit):
        rows = self._query(
            "SELECT ts, value FROM telemetry WHERE node = %s AND metric = %s AND ts >= %s AND ts <= %s "
            "ORDER BY ts LIMIT %s",
            (node, metric, _dt(start), _dt(end), limit),
        )
        return [{"ts": _unix(r["ts"]), "value": r["value"]} for r in rows]

    def events(self, node, type_, limit):
        where, params = [], []
        if node:
            where.append("node = %s")
            params.append(node)
        if type_:
            where.append("type = %s")
            params.append(type_)
        sql = "SELECT ts, node, type, state, reason, data FROM events"
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = self._query(sql + " ORDER BY ts DESC LIMIT %s", (*params, limit))
        out = []
        for r in rows:
            event = {"ts": _unix(r["ts"]), "node": r["node"], "type": r["type"], "state": r["state"]}
            if r["reason"]:
                event["reason"] = r["reason"]
            event.update(r["data"] or {})
            out.append(event)
        return out
