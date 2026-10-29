-- Schema for GreenLoop Farm readings. Runs once, on the first start of the db container.
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- One row per metric per telemetry message (long format, so new metrics need no migration).
CREATE TABLE IF NOT EXISTS telemetry (
    ts      TIMESTAMPTZ      NOT NULL,
    node    TEXT             NOT NULL,
    metric  TEXT             NOT NULL,
    value   DOUBLE PRECISION NOT NULL
);
SELECT create_hypertable('telemetry', 'ts', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS telemetry_node_metric_ts ON telemetry (node, metric, ts DESC);

-- Door, pump and motion events. Extra payload fields are kept in `data`.
CREATE TABLE IF NOT EXISTS events (
    ts      TIMESTAMPTZ NOT NULL,
    node    TEXT        NOT NULL,
    type    TEXT        NOT NULL,
    state   TEXT,
    reason  TEXT,
    data    JSONB       NOT NULL DEFAULT '{}'::jsonb
);
SELECT create_hypertable('events', 'ts', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS events_node_type_ts ON events (node, type, ts DESC);

-- Latest online/offline status and last time anything was heard from each node.
CREATE TABLE IF NOT EXISTS node_status (
    node       TEXT PRIMARY KEY,
    status     TEXT        NOT NULL,
    last_seen  TIMESTAMPTZ NOT NULL
);
