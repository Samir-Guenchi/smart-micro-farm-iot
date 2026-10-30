import json
from types import SimpleNamespace

import pytest

from greenloop_agent.agent import FarmAgent
from greenloop_agent.approvals import EXPIRES_S, Approvals
from greenloop_agent.farm import MockFarm
from greenloop_agent.log import DecisionLog
from greenloop_agent.telegram import Telegram
from greenloop_agent.tools import Suggestion, ToolError, Toolbox


def tool_use(id, name, **input):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


def text(t):
    return SimpleNamespace(type="text", text=t)


class ScriptedClient:
    """Fake anthropic client that replays a fixed list of responses and records requests."""

    def __init__(self, *turns):
        self.turns = list(turns)
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(json.loads(json.dumps(kwargs, default=lambda o: o.__dict__)))
        content = self.turns.pop(0)
        stop = "tool_use" if any(b.type == "tool_use" for b in content) else "end_turn"
        return SimpleNamespace(stop_reason=stop, content=content)


@pytest.fixture
def farm():
    return MockFarm()


def test_fixture_tells_the_expected_story(farm):
    tb = Toolbox(farm)
    w1 = tb.run("get_readings", {"node": "irrigation-1", "metric": "water_liters", "hours": 168})["sum"]
    w2 = tb.run("get_readings", {"node": "irrigation-2", "metric": "water_liters", "hours": 168})["sum"]
    assert w2 > w1  # bed 2 used the most water this week
    door = tb.run("get_events", {"node": "coop-1", "type": "door", "limit": 50})
    assert sum(e["state"] == "closed" for e in door) == 6  # one missed close in 7 days


def test_readings_are_summarized_not_dumped(farm):
    out = Toolbox(farm).run("get_readings", {"node": "irrigation-2", "metric": "soil_moisture_pct", "hours": 168})
    assert out["count"] == 168 and len(out["points"]) <= 48
    assert set(out) >= {"min", "max", "avg", "last"}


def test_read_only_question_runs_tools_and_offers_no_action_tool(farm):
    client = ScriptedClient(
        [tool_use("t1", "list_nodes"), tool_use("t2", "get_forecast")],
        [text("All nodes are online and no rain is forecast.")],
    )
    answer = FarmAgent(farm, client=client).ask("How is the farm today?")
    assert answer == "All nodes are online and no rain is forecast."
    tool_names = {t["name"] for t in client.calls[0]["tools"]}
    assert "suggest_watering" not in tool_names
    results = client.calls[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["t1", "t2"]  # both results in one message
    assert client.calls[0]["model"] == "claude-opus-5-5" and client.calls[0]["fallbacks"] == "default"


def test_daily_check_collects_a_suggestion_without_touching_the_pump(farm):
    client = ScriptedClient(
        [tool_use("t1", "get_readings", node="irrigation-2", metric="soil_moisture_pct", hours=24)],
        [tool_use("t2", "suggest_watering", node="irrigation-2", duration_min=15, when="tonight", reason="Bed 2 is at 18% and no rain is forecast.")],
        [text("Bed 2 is dry; I suggest watering it tonight.")],
    )
    report, suggestions = FarmAgent(farm, client=client).daily_check()
    assert len(suggestions) == 1 and suggestions[0].node == "irrigation-2" and suggestions[0].duration_s == 900
    assert farm.pump_calls == []
    assert "suggest_watering" in {t["name"] for t in client.calls[0]["tools"]}


@pytest.mark.parametrize(
    "args, message",
    [
        ({"node": "coop-1", "duration_min": 5, "when": "now", "reason": "x"}, "never actioned"),
        ({"node": "hive-1", "duration_min": 5, "when": "now", "reason": "x"}, "Only irrigation"),
        ({"node": "irrigation-9", "duration_min": 5, "when": "now", "reason": "x"}, "Unknown node"),
        ({"node": "irrigation-1", "duration_min": 60, "when": "now", "reason": "x"}, "between 1 and 15"),
    ],
)
def test_unsafe_suggestions_are_refused(farm, args, message):
    with pytest.raises(ToolError, match=message):
        Toolbox(farm).run("suggest_watering", args)


def test_refused_suggestion_goes_back_to_the_model_as_an_error(farm):
    client = ScriptedClient(
        [tool_use("t1", "suggest_watering", node="coop-1", duration_min=5, when="now", reason="door")],
        [text("The coop door did not close; please check it.")],
    )
    _, suggestions = FarmAgent(farm, client=client).daily_check()
    assert suggestions == []
    result = client.calls[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True


def test_suggestion_tool_is_rejected_in_read_only_mode(farm):
    with pytest.raises(ToolError):
        Toolbox(farm, allow_suggestions=False).run("suggest_watering", {"node": "irrigation-1", "duration_min": 5, "when": "now", "reason": "x"})


def make_approvals(tmp_path, farm, now=1000.0):
    clock = SimpleNamespace(t=now)
    approvals = Approvals(farm, DecisionLog(tmp_path / "log.jsonl"), clock=lambda: clock.t)
    s = Suggestion("abc123", "water", "irrigation-2", 900, "tonight", "dry")
    approvals.record(s, "report")
    return approvals, clock


def test_approve_calls_pump_once_and_logs_everything(tmp_path, farm):
    approvals, _ = make_approvals(tmp_path, farm)
    assert approvals.decide("abc123", "approve", by="test").startswith("Approved")
    assert farm.pump_calls == [{"node": "irrigation-2", "duration_s": 900}]
    assert approvals.decide("abc123", "approve", by="test") == "Already approved."
    assert len(farm.pump_calls) == 1
    kinds = [e["kind"] for e in approvals.log.entries("abc123")]
    assert kinds == ["suggested", "decided", "outcome"]


def test_reject_never_calls_pump(tmp_path, farm):
    approvals, _ = make_approvals(tmp_path, farm)
    assert approvals.decide("abc123", "reject", by="test").startswith("Rejected")
    assert farm.pump_calls == []
    assert approvals.decide("abc123", "approve", by="test") == "Already rejected."
    assert farm.pump_calls == []


def test_stale_suggestion_expires(tmp_path, farm):
    approvals, clock = make_approvals(tmp_path, farm)
    clock.t += EXPIRES_S + 1
    assert "expired" in approvals.decide("abc123", "approve", by="test")
    assert farm.pump_calls == []


def test_pump_failure_is_logged(tmp_path, farm):
    approvals, _ = make_approvals(tmp_path, farm)
    farm.pump = lambda node, d: (_ for _ in ()).throw(OSError("api down"))
    assert "failed" in approvals.decide("abc123", "approve", by="test")
    assert approvals.log.entries("abc123")[-1] == {**approvals.log.entries("abc123")[-1], "kind": "outcome", "ok": False}


class FakeTelegram(Telegram):
    def __init__(self):
        super().__init__("token", "42")
        self.sent = []

    def call(self, method, **params):
        self.sent.append((method, params))
        return {"message_id": 1}


def update(chat_id, data):
    return {"update_id": 1, "callback_query": {"id": "cb", "data": data, "from": {"username": "farmer"},
            "message": {"message_id": 7, "chat": {"id": chat_id}, "text": "Suggestion"}}}


def test_telegram_buttons_and_approve_tap(tmp_path, farm):
    approvals, _ = make_approvals(tmp_path, farm)
    tg = FakeTelegram()
    tg.send_suggestion(Suggestion("abc123", "water", "irrigation-2", 900, "tonight", "dry"))
    buttons = tg.sent[0][1]["reply_markup"]["inline_keyboard"][0]
    assert [b["callback_data"] for b in buttons] == ["approve:abc123", "reject:abc123"]
    assert tg.handle_update(update(42, "approve:abc123"), approvals).startswith("Approved")
    assert farm.pump_calls and approvals.log.entries("abc123")[1]["by"] == "telegram:farmer"


def test_telegram_ignores_taps_from_other_chats(tmp_path, farm):
    approvals, _ = make_approvals(tmp_path, farm)
    assert FakeTelegram().handle_update(update(999, "approve:abc123"), approvals) is None
    assert farm.pump_calls == []
