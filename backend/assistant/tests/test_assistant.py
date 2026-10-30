import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from greenloop_assistant.core import IDK, Assistant, detect_language
from greenloop_assistant.knowledge import CropCalendar, KnowledgeBase, parse_front_matter

HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parent / "sample-knowledge"
CALENDAR = HERE.parents[2] / "data" / "crop-calendar.json"


class FakeClient:
    """Stands in for anthropic.Anthropic(): records the request and returns a canned reply."""

    def __init__(self, text="Water at the base in the morning [tomato-late-blight].", stop_reason="end_turn"):
        self.calls = []
        self.text = text
        self.stop_reason = stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            stop_reason=self.stop_reason,
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=self.text)],
        )


@pytest.fixture
def assistant():
    return Assistant(SAMPLE, CALENDAR, client=FakeClient())


def test_front_matter_parses_lists_and_strings():
    meta, body = parse_front_matter('---\ntitle: "A"\ncrops: [tomato, potato]\nreviewed: false\n---\n\n# A\n')
    assert meta == {"title": "A", "crops": ["tomato", "potato"], "reviewed": False}
    assert body.startswith("# A")


def test_full_knowledge_base_loads_and_skips_template():
    kb = KnowledgeBase.load(HERE.parents[2] / "knowledge")
    slugs = {n.slug for n in kb.notes}
    assert len(slugs) >= 30
    assert "_template" not in slugs and "README" not in slugs


@pytest.mark.parametrize(
    "question, slug",
    [
        ("My tomato leaves have brown patches after rain", "tomato-late-blight"),
        ("How do I compost chicken manure?", "composting-poultry-manure"),
        ("How much drip water do tomatoes need each week?", "drip-irrigation-schedule"),
        ("What protein feed do quail need?", "quail-care"),
        ("When should I add supers to the hives?", "beekeeping-calendar"),
        ("Comment composter le fumier de poules ?", "composting-poultry-manure"),
    ],
)
def test_search_finds_the_right_note(assistant, question, slug):
    hits = assistant.kb.search(question)
    assert hits and hits[0].note.slug == slug


def test_search_returns_nothing_for_unrelated_question(assistant):
    assert assistant.kb.search("What is the capital of Peru?") == []


def test_calendar_parses_country_month_and_crop():
    q = CropCalendar.parse("When do I plant potatoes in Latvia in May?")
    assert (q.country, q.month, q.crops) == ("LV", 5, ["potato"])
    q = CropCalendar.parse("متى أزرع البطاطا في الجزائر؟")
    assert (q.country, q.crops) == ("DZ", ["potato"])


def test_calendar_defaults_to_this_month_when_no_crop_or_month():
    cal = CropCalendar.load(CALENDAR)
    q, rows = cal.lookup("What should I sow in Morocco?", today_month=10)
    assert q.month == 10 and rows and all(r["country"] == "MA" and r["month"] == 10 for r in rows)


def test_unknown_question_says_i_dont_know_without_calling_the_model(assistant):
    answer = assistant.ask("How do I fix my car engine?")
    assert answer.text == IDK["en"] and not answer.used_llm
    assert assistant.client.calls == []


def test_i_dont_know_in_the_question_language(assistant):
    assert assistant.ask("Comment réparer ma voiture ?").text == IDK["fr"]
    assert assistant.ask("كيف أصلح سيارتي؟").text == IDK["ar"]


def test_answer_cites_sources_and_request_is_well_formed(assistant):
    answer = assistant.ask("My tomato leaves have brown patches after rain")
    assert answer.used_llm
    assert [s["slug"] for s in answer.sources] == ["tomato-late-blight"]
    call = assistant.client.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default" and call["betas"] == ["server-side-fallback-2026-07-01"]
    assert "thinking" not in call and "temperature" not in call
    prompt = call["messages"][0]["content"]
    assert '<note slug="tomato-late-blight"' in prompt and IDK["en"] in prompt


def test_calendar_rows_go_into_the_prompt():
    a = Assistant(SAMPLE, CALENDAR, client=FakeClient("Plant in May [calendar]."))
    answer = a.ask("When do I plant potatoes in Latvia?", today=dt.date(2026, 1, 1))
    assert answer.sources == [{"type": "calendar", "country": "LV", "month": None, "rows": 6}]
    assert '<calendar country="Latvia"' in a.client.calls[0]["messages"][0]["content"]


def test_refusal_falls_back_to_i_dont_know():
    a = Assistant(SAMPLE, CALENDAR, client=FakeClient("", stop_reason="refusal"))
    assert a.ask("tomato blight").text == IDK["en"]


def test_language_detection():
    assert detect_language("When do I plant potatoes?") == "en"
    assert detect_language("Quand planter les pommes de terre ?") == "fr"
    assert detect_language("متى أزرع البطاطا؟") == "ar"


def test_chat_endpoint(monkeypatch):
    from fastapi.testclient import TestClient

    from greenloop_assistant import server

    monkeypatch.setattr(server, "assistant", Assistant(SAMPLE, CALENDAR, client=FakeClient()))
    c = TestClient(server.app)
    r = c.post("/api/assistant/chat", json={"question": "tomato leaves brown patches after rain"})
    assert r.status_code == 200
    assert r.json()["sources"][0]["slug"] == "tomato-late-blight"
    assert c.post("/api/assistant/chat", json={"question": ""}).status_code == 422
    assert c.get("/").status_code == 200


def test_eval_set_is_valid():
    items = [json.loads(l) for l in (HERE.parent / "evals" / "questions.jsonl").read_text().splitlines() if l.strip()]
    assert len(items) >= 20
    for it in items:
        assert set(it) >= {"id", "question", "expected_sources", "must_include"}


def test_nvidia_client_answers_in_the_same_shape():
    from greenloop_assistant import llm

    reply = SimpleNamespace(content="Water at the base [tomato-late-blight].", tool_calls=None)
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: SimpleNamespace(choices=[SimpleNamespace(message=reply, finish_reason="stop")]))))
    a = Assistant(SAMPLE, CALENDAR, client=llm.NvidiaClient(openai_client=fake))
    answer = a.ask("My tomato leaves have brown patches after rain")
    assert answer.used_llm and answer.sources[0]["slug"] == "tomato-late-blight"
