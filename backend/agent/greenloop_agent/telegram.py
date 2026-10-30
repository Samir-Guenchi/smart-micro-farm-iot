"""Telegram delivery: send suggestions with Approve / Reject buttons and handle the taps.

Uses the Bot API directly over HTTPS (long polling), so no extra dependency.
Only taps from TELEGRAM_CHAT_ID are accepted.
"""
from __future__ import annotations

import json
import time
import urllib.request

from .approvals import Approvals
from .tools import Suggestion


class Telegram:
    def __init__(self, token: str, chat_id: str, timeout: float = 40):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = str(chat_id)
        self.timeout = timeout

    def call(self, method: str, **params):
        req = urllib.request.Request(
            f"{self.base}/{method}", data=json.dumps(params).encode(), headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout + 10) as r:
            data = json.loads(r.read())
        if not data.get("ok"):
            raise RuntimeError(f"Telegram {method} failed: {data}")
        return data["result"]

    def send_report(self, text: str):
        return self.call("sendMessage", chat_id=self.chat_id, text=text[:4000])

    def send_suggestion(self, s: Suggestion):
        text = f"💧 Suggestion: water {s.node.replace('irrigation-', 'bed ')} for {s.duration_s // 60} min ({s.when}).\n\nWhy: {s.reason}"
        keyboard = {"inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve:{s.id}"},
            {"text": "❌ Reject", "callback_data": f"reject:{s.id}"},
        ]]}
        return self.call("sendMessage", chat_id=self.chat_id, text=text, reply_markup=keyboard)

    def handle_update(self, update: dict, approvals: Approvals) -> str | None:
        cb = update.get("callback_query")
        if not cb:
            return None
        msg = cb.get("message") or {}
        if str((msg.get("chat") or {}).get("id")) != self.chat_id:
            self.call("answerCallbackQuery", callback_query_id=cb["id"], text="Not allowed.")
            return None
        decision, _, sid = str(cb.get("data", "")).partition(":")
        if decision not in ("approve", "reject") or not sid:
            return None
        who = (cb.get("from") or {}).get("username") or str((cb.get("from") or {}).get("id"))
        reply = approvals.decide(sid, decision, by=f"telegram:{who}")
        self.call("answerCallbackQuery", callback_query_id=cb["id"], text=reply[:180])
        # Replace the buttons with the result, so nobody taps twice.
        self.call("editMessageText", chat_id=self.chat_id, message_id=msg["message_id"], text=f"{msg.get('text', '')}\n\n→ {reply}")
        return reply

    def poll_forever(self, approvals: Approvals):
        offset = None
        while True:
            try:
                updates = self.call("getUpdates", timeout=int(self.timeout), offset=offset, allowed_updates=["callback_query"])
            except Exception as e:
                print("telegram poll failed:", e)
                time.sleep(5)
                continue
            for u in updates:
                offset = u["update_id"] + 1
                try:
                    self.handle_update(u, approvals)
                except Exception as e:
                    print("could not handle update:", e)
