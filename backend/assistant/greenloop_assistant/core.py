"""Answer a farming question from the knowledge base and crop calendar with Claude or an NVIDIA-hosted model."""
from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import llm
from .llm import NotConfigured
from .knowledge import COUNTRY_NAMES, MONTH_NAMES, CropCalendar, KnowledgeBase

BACKEND = Path(__file__).resolve().parents[2]
DEFAULT_KNOWLEDGE = BACKEND / "knowledge"
DEFAULT_CALENDAR = BACKEND / "data" / "crop-calendar.json"

MODEL = os.environ.get("ASSISTANT_MODEL", "claude-opus-5-5")
# Chat answers from a few short notes; low effort keeps replies fast and cheap.
EFFORT = os.environ.get("ASSISTANT_EFFORT", "low")

IDK = {
    "en": "I don't know. None of the farm's notes or the crop calendar cover that yet.",
    "fr": "Je ne sais pas. Aucune note de la ferme ni le calendrier des cultures ne couvrent encore ce sujet.",
    "ar": "لا أعرف. لا تغطي ملاحظات المزرعة ولا تقويم المحاصيل هذا الموضوع بعد.",
}

SYSTEM = """You are the GreenLoop Farm assistant, helping small farmers with practical questions.

Answer only from the sources given in the user's message: farm knowledge notes and crop calendar rows. Do not use outside knowledge to add facts the sources do not contain.

- If the sources do not answer the question, reply exactly with the "I don't know" sentence given in the message, in the question's language, and nothing else.
- Cite every source you use inline as [slug] for notes or [calendar] for calendar rows. Only cite slugs that appear in the sources.
- Be short and practical: a direct answer first, then a few steps if useful. Plain language, no jargon.
- Answer in the same language as the question (English, French or Arabic are the usual ones).
- When advice depends on country or region and the farmer did not say where they are, say which region the advice is for."""


@dataclass
class Answer:
    text: str
    sources: list[dict] = field(default_factory=list)
    used_llm: bool = False


def detect_language(text: str) -> str:
    if any("؀" <= ch <= "ۿ" for ch in text):
        return "ar"
    lowered = f" {text.lower()} "
    french = [" je ", " quand ", " comment ", " est-ce ", " mes ", " les ", " des ", " pour ", " planter", " semer", " poules"]
    if any(w in lowered for w in french) or any(ch in text for ch in "éèàçêù"):
        return "fr"
    return "en"


class Assistant:
    def __init__(self, knowledge_dir: Path = DEFAULT_KNOWLEDGE, calendar_path: Path = DEFAULT_CALENDAR, client=None):
        self.kb = KnowledgeBase.load(knowledge_dir)
        self.calendar = CropCalendar.load(calendar_path)
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = llm.make_client()
        return self._client

    def retrieve(self, question: str, today: dt.date | None = None):
        today = today or dt.date.today()
        hits = self.kb.search(question)
        cal_query, rows = self.calendar.lookup(question, today_month=today.month)
        return hits, cal_query, rows

    def build_prompt(self, question: str, lang: str, hits, cal_query, rows) -> str:
        parts = ["<sources>"]
        for h in hits:
            parts.append(f'<note slug="{h.note.slug}" title="{h.note.title}">\n{h.note.body.strip()}\n</note>')
        if rows:
            where = COUNTRY_NAMES.get(cal_query.country, cal_query.country)
            when = MONTH_NAMES[cal_query.month - 1] if cal_query.month else "all months"
            lines = [f"- {MONTH_NAMES[r['month'] - 1]}, {r['crop'].replace('_', ' ')}: {r['action']}. {r['notes']}" for r in rows]
            parts.append(f'<calendar country="{where}" month="{when}">\n' + "\n".join(lines) + "\n</calendar>")
        parts.append("</sources>")
        parts.append(f'"I don\'t know" sentence: {IDK[lang]}')
        parts.append(f"<question>\n{question}\n</question>")
        return "\n\n".join(parts)

    def ask(self, question: str, today: dt.date | None = None) -> Answer:
        question = question.strip()
        lang = detect_language(question)
        hits, cal_query, rows = self.retrieve(question, today)
        sources = [{"type": "note", "slug": h.note.slug, "title": h.note.title} for h in hits]
        if rows:
            sources.append({"type": "calendar", "country": cal_query.country, "month": cal_query.month, "rows": len(rows)})
        if not sources:
            # Nothing relevant: say so without spending an API call or inviting a guess.
            return Answer(IDK[lang])

        try:
            response = self._create(question, lang, hits, cal_query, rows)
        except TypeError as e:
            # The SDK raises TypeError when it finds no credentials at all.
            if "authentication" in str(e):
                raise NotConfigured(str(e)) from e
            raise
        if response.stop_reason == "refusal":
            return Answer(IDK[lang], [], used_llm=True)
        text = "".join(b.text for b in response.content if b.type == "text").strip() or IDK[lang]
        # Keep only the sources the answer actually cites, so the UI does not list unused notes.
        cited = [s for s in sources if (f"[{s['slug']}]" in text if s["type"] == "note" else "[calendar]" in text)]
        return Answer(text, cited, used_llm=True)

    def _create(self, question, lang, hits, cal_query, rows):
        return self.client.beta.messages.create(
            model=llm.model_for(MODEL),
            max_tokens=16000,
            system=SYSTEM,
            output_config={"effort": EFFORT},
            # On a safety decline, re-run on a fallback model instead of failing the answer.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": self.build_prompt(question, lang, hits, cal_query, rows)}],
        )
