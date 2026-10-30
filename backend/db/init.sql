-- Schema for GreenLoop Farm readings. Runs once, on the first start of the db container,
-- and on every start of the API on Render (db/migrate.py). Safe to run again.
-- TimescaleDB is used when available; on plain Postgres (e.g. Render) the tables stay normal tables.
DO $$ BEGIN
    CREATE EXTENSION IF NOT EXISTS timescaledb;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'TimescaleDB not available, using plain tables';
END $$;

-- One row per metric per telemetry message (long format, so new metrics need no migration).
CREATE TABLE IF NOT EXISTS telemetry (
    ts      TIMESTAMPTZ      NOT NULL,
    node    TEXT             NOT NULL,
    metric  TEXT             NOT NULL,
    value   DOUBLE PRECISION NOT NULL
);
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('telemetry', 'ts', if_not_exists => TRUE);
    END IF;
END $$;
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
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('events', 'ts', if_not_exists => TRUE);
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS events_node_type_ts ON events (node, type, ts DESC);

-- Latest online/offline status and last time anything was heard from each node.
CREATE TABLE IF NOT EXISTS node_status (
    node       TEXT PRIMARY KEY,
    status     TEXT        NOT NULL,
    last_seen  TIMESTAMPTZ NOT NULL
);
