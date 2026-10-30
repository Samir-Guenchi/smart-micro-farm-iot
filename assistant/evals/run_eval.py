"""Run the assistant's eval set before each change.

  python evals/run_eval.py            # retrieval only: free, no API key needed
  python evals/run_eval.py --live     # also asks Claude and checks the answers

Each line of questions.jsonl has:
  expected_sources  note slugs (or "calendar") that must be retrieved; [] means
                    the assistant should say "I don't know"
  must_include      groups of words; the answer must contain at least one word
                    from every group (case-insensitive). Checked with --live only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenloop_assistant import load_env  # noqa: E402
from greenloop_assistant.core import Assistant  # noqa: E402

TODAY = dt.date(2026, 10, 15)  # fixed so "this month" questions are reproducible


def retrieved(assistant: Assistant, question: str) -> set[str]:
    hits, _, rows = assistant.retrieve(question, TODAY)
    return {h.note.slug for h in hits} | ({"calendar"} if rows else set())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="call Claude and check answer content")
    args = ap.parse_args()
    load_env()
    items = [json.loads(l) for l in (Path(__file__).parent / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assistant = Assistant()
    failures = 0
    for it in items:
        got = retrieved(assistant, it["question"])
        want = set(it["expected_sources"])
        ok = want <= got if want else not got
        detail = f"retrieved {sorted(got)}"
        if ok and args.live:
            answer = assistant.ask(it["question"], TODAY)
            text = answer.text.lower()
            missing = [g for g in it["must_include"] if not any(w.lower() in text for w in g)]
            ok = not missing
            detail = f"missing one of {missing}" if missing else "answer ok"
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {it['id']:<16} {detail}")
    print(f"\n{len(items) - failures}/{len(items)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
