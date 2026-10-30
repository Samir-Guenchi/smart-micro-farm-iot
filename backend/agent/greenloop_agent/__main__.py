"""Command line for the farm agent.

  python -m greenloop_agent ask "how is the farm today?"   read-only question
  python -m greenloop_agent check                           daily check, print suggestions
  python -m greenloop_agent check --send                    daily check, send report + suggestions to Telegram
  python -m greenloop_agent bot                             wait for Approve / Reject taps
  python -m greenloop_agent log                             show the decision log

Add --mock to use fixtures/week.json instead of the real API (pump calls are not sent).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import load_env
from .agent import FarmAgent
from .approvals import Approvals
from .farm import FarmAPI, MockFarm
from .log import DecisionLog

LOG = Path(os.environ.get("AGENT_LOG", Path(__file__).resolve().parent.parent / "data" / "decisions.jsonl"))


def make_farm(mock: bool):
    if mock:
        return MockFarm()
    return FarmAPI(
        os.environ.get("API_BASE_URL", "http://localhost:8000/api"),
        os.environ["API_TOKEN"],
        float(os.environ.get("FARM_LAT", "56.95")),
        float(os.environ.get("FARM_LON", "24.11")),
    )


def telegram():
    from .telegram import Telegram

    return Telegram(os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"])


def main():
    load_env()
    ap = argparse.ArgumentParser(prog="greenloop_agent")
    ap.add_argument("--mock", action="store_true", help="use fixture data instead of the real API")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ask").add_argument("question", nargs="+")
    sub.add_parser("check").add_argument("--send", action="store_true", help="send to Telegram")
    sub.add_parser("bot")
    sub.add_parser("log")
    args = ap.parse_args()

    log = DecisionLog(LOG)
    if args.cmd == "log":
        for e in log.entries():
            print(json.dumps(e, ensure_ascii=False))
        return
    farm = make_farm(args.mock)
    approvals = Approvals(farm, log)
    if args.cmd == "ask":
        print(FarmAgent(farm).ask(" ".join(args.question)))
    elif args.cmd == "check":
        report, suggestions = FarmAgent(farm).daily_check()
        for s in suggestions:
            approvals.record(s, report)
        print(report)
        for s in suggestions:
            print(f"\nSuggestion {s.id}: water {s.node} for {s.duration_s // 60} min ({s.when}). {s.reason}")
        if args.send:
            tg = telegram()
            tg.send_report(report)
            for s in suggestions:
                tg.send_suggestion(s)
    elif args.cmd == "bot":
        telegram().poll_forever(approvals)


if __name__ == "__main__":
    main()
