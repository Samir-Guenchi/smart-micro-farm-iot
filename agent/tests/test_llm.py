import json
from types import SimpleNamespace

from greenloop_agent import llm
from greenloop_agent.agent import FarmAgent
from greenloop_agent.farm import MockFarm


def completion(content=None, tool_calls=(), finish="stop"):
    calls = [SimpleNamespace(id=i, function=SimpleNamespace(name=n, arguments=json.dumps(a))) for i, n, a in tool_calls]
    msg = SimpleNamespace(content=content, tool_calls=calls or None)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason=finish)])


class FakeOpenAI:
    """Stands in for openai.OpenAI(): replays completions and records requests."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(json.loads(json.dumps(kwargs)))
        return self.replies.pop(0)


def test_provider_defaults_to_nvidia_only_when_its_key_is_the_only_one(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    assert llm.provider() == "anthropic"
    monkeypatch.setenv("NVIDIA_API_KEY", "test")
    assert llm.provider() == "nvidia"
    assert llm.model_for("claude-opus-5-5") == llm.NVIDIA_MODEL
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    assert llm.provider() == "anthropic"
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    assert llm.provider() == "nvidia"


def test_agent_tool_loop_runs_over_an_openai_compatible_api():
    fake = FakeOpenAI(
        completion(tool_calls=[("c1", "list_nodes", {}), ("c2", "get_forecast", {})], finish="tool_calls"),
        completion("<think>checking</think>All nodes are online."),
    )
    agent = FarmAgent(MockFarm(), client=llm.NvidiaClient(openai_client=fake), model="meta/llama-3.3-70b-instruct")
    assert agent.ask("How is the farm today?") == "All nodes are online."

    first, second = fake.calls
    assert first["messages"][0]["role"] == "system"
    assert first["max_tokens"] <= llm.NVIDIA_MAX_TOKENS
    assert "suggest_watering" not in {t["function"]["name"] for t in first["tools"]}
    roles = [m["role"] for m in second["messages"]]
    assert roles == ["system", "user", "assistant", "tool", "tool"]
    assert [c["id"] for c in second["messages"][2]["tool_calls"]] == ["c1", "c2"]
    assert second["messages"][3]["tool_call_id"] == "c1"


def test_tool_errors_are_passed_back_as_text():
    msgs = llm.to_openai_messages(None, [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1", "content": "no such node", "is_error": True}]}])
    assert msgs == [{"role": "tool", "tool_call_id": "c1", "content": "Error: no such node"}]
