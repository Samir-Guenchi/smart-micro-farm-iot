import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import auth  # noqa: E402
import main  # noqa: E402
from settings import Settings  # noqa: E402

NOW = int(time.time())


class FakeStore:
    def __init__(self):
        self.calls = []

    def nodes(self):
        return [
            {"id": "coop-1", "status": "online", "last_seen": NOW - 3600, "latest": {"air_temp_c": 19.0}},
            {"id": "irrigation-1", "status": "online", "last_seen": NOW - 30, "latest": {"soil_moisture_pct": 41.2}},
        ]

    def readings(self, node, metric, start, end, limit):
        self.calls.append(("readings", node, metric, start, end, limit))
        return [{"ts": start, "value": 41.2}, {"ts": end, "value": 40.0}]

    def events(self, node, type_, limit):
        self.calls.append(("events", node, type_, limit))
        return [{"ts": NOW, "node": "coop-1", "type": "door", "state": "closed"}]


class FakePublisher:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def command(self, node, payload):
        if self.fail:
            raise ConnectionRefusedError("broker down")
        self.sent.append((node, payload))


@pytest.fixture
def settings():
    return Settings(admin_user="farmer", admin_password="s3cret", secret_key="test-key", service_token="svc-token")


@pytest.fixture
def ctx(settings):
    store, pub = FakeStore(), FakePublisher()
    main.app.dependency_overrides = {
        main.get_settings: lambda: settings,
        main.get_store: lambda: store,
        main.get_publisher: lambda: pub,
    }
    token, _ = auth.issue_token(settings, "farmer")
    client = TestClient(main.app, headers={"Authorization": f"Bearer {token}"})
    yield client, store, pub
    main.app.dependency_overrides = {}


def test_login_returns_working_token(ctx):
    client, _, _ = ctx
    anon = TestClient(main.app)
    assert anon.post("/api/login", json={"username": "farmer", "password": "nope"}).status_code == 401
    r = anon.post("/api/login", json={"username": "farmer", "password": "s3cret"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert anon.get("/api/nodes", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_every_farm_endpoint_requires_a_token(ctx):
    anon = TestClient(main.app)
    for method, path in [("get", "/api/nodes"), ("get", "/api/readings?node=a&metric=b"), ("get", "/api/events"),
                         ("post", "/api/nodes/irrigation-1/pump")]:
        assert getattr(anon, method)(path).status_code == 401
        assert getattr(anon, method)(path, headers={"Authorization": "Bearer forged.1.abc"}).status_code == 401


def test_expired_and_tampered_tokens_are_rejected(settings):
    token, _ = auth.issue_token(settings, "farmer", now=time.time() - 10 * 365 * 86400)
    assert auth.verify_token(settings, token) is None
    good, _ = auth.issue_token(settings, "farmer")
    user, exp, sig = good.split(".")
    assert auth.verify_token(settings, f"admin.{exp}.{sig}") is None
    assert auth.verify_token(settings, good) == "farmer"
    assert auth.verify_token(settings, "svc-token") == "service"


def test_login_disabled_without_admin_password():
    assert not auth.check_password(Settings(admin_password=""), "admin", "")


def test_nodes_marks_stale_nodes_offline(ctx):
    client, _, _ = ctx
    nodes = {n["id"]: n for n in client.get("/api/nodes").json()}
    assert nodes["irrigation-1"] == {"id": "irrigation-1", "status": "online", "last_seen": NOW - 30, "latest": {"soil_moisture_pct": 41.2}}
    assert nodes["coop-1"]["status"] == "offline"


def test_readings_passes_filters_and_defaults_to_last_24h(ctx):
    client, store, _ = ctx
    r = client.get("/api/readings", params={"node": "irrigation-1", "metric": "soil_moisture_pct", "from": 100, "to": 200})
    assert r.json() == [{"ts": 100, "value": 41.2}, {"ts": 200, "value": 40.0}]
    assert store.calls[-1] == ("readings", "irrigation-1", "soil_moisture_pct", 100, 200, 5000)
    client.get("/api/readings", params={"node": "irrigation-1", "metric": "soil_moisture_pct"})
    _, _, _, start, end, _ = store.calls[-1]
    assert end - start == 24 * 3600 and abs(end - time.time()) < 5
    assert client.get("/api/readings", params={"node": "a", "metric": "b", "from": 300, "to": 200}).status_code == 422
    assert client.get("/api/readings", params={"node": "a"}).status_code == 422


def test_events_filters_and_limit(ctx):
    client, store, _ = ctx
    r = client.get("/api/events", params={"node": "coop-1", "type": "door", "limit": 5})
    assert r.json()[0]["state"] == "closed"
    assert store.calls[-1] == ("events", "coop-1", "door", 5)
    assert client.get("/api/events", params={"limit": 1000}).status_code == 422


def test_pump_publishes_capped_command(ctx):
    client, _, pub = ctx
    r = client.post("/api/nodes/irrigation-1/pump", json={"duration_s": 600})
    assert r.status_code == 202 and r.json() == {"ok": True, "duration_s": 600}
    r = client.post("/api/nodes/irrigation-1/pump", json={"duration_s": 99999})
    assert r.json()["duration_s"] == 900
    assert pub.sent == [("irrigation-1", {"action": "pump", "duration_s": 600}), ("irrigation-1", {"action": "pump", "duration_s": 900})]


def test_pump_rejects_bad_requests(ctx):
    client, _, pub = ctx
    assert client.post("/api/nodes/coop-1/pump", json={"duration_s": 60}).status_code == 404
    assert client.post("/api/nodes/irrigation-1/pump", json={"duration_s": 0}).status_code == 422
    assert client.post("/api/nodes/irrigation-1/pump", json={}).status_code == 422
    assert pub.sent == []


def test_pump_reports_broker_down(ctx, settings):
    client, _, _ = ctx
    main.app.dependency_overrides[main.get_publisher] = lambda: FakePublisher(fail=True)
    assert client.post("/api/nodes/irrigation-1/pump", json={"duration_s": 60}).status_code == 503


def test_openapi_docs_are_served(ctx):
    anon = TestClient(main.app)
    assert anon.get("/api/docs").status_code == 200
    paths = anon.get("/api/openapi.json").json()["paths"]
    assert {"/api/nodes", "/api/readings", "/api/events", "/api/nodes/{node_id}/pump", "/api/login"} <= set(paths)
