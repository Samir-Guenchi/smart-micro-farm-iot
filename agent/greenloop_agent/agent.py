"""The agent loop: Claude with read tools over the farm API, plus a suggest-only action tool."""
from __future__ import annotations

import json
import os

import anthropic

from .tools import Suggestion, ToolError, Toolbox

MODEL = os.environ.get("AGENT_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("AGENT_EFFORT", "medium")
MAX_TURNS = 12

SYSTEM = """You are the GreenLoop Farm agent. You look after one small farm through its sensors: drip-irrigated vegetable beds (irrigation-N is bed N), beehives (hive-N) and a chicken coop with an automatic door (coop-1).

How to work:
- Base every statement on data from your tools. Call them before answering; never guess readings.
- Give times in plain words and say how fresh the data is if a node looks stale or offline.
- Be brief and concrete, like a helpful farmhand texting the farmer. Answer in the farmer's language.

Actions:
- You cannot act on the farm yourself. You can only propose watering with suggest_watering; the farmer approves or rejects each suggestion.
- Suggest watering only when the readings support it: soil moisture below about 25% (or clearly falling toward it before the next scheduled watering) and no meaningful rain forecast (under about 3 mm in the next 24 hours). Prefer evening or early morning. Typical runs are 10–15 minutes.
- Never suggest anything for the coop door, the hives or the animals. If something there looks wrong (for example the door did not close), report it so the farmer can check in person.
- If nothing needs doing, say so in one line. Not suggesting anything is a good outcome."""

DAILY_CHECK = """Do the daily farm check now. Look at every node, the last 24-48 hours of soil moisture and water use for each bed, recent door and pump events, and the forecast. Then:
1. Propose watering (suggest_watering) for any bed that needs it.
2. Finish with a short report for the farmer: anything wrong or unusual first, then one line per area (beds, hives, coop). Mention every suggestion you made."""


class FarmAgent:
    def __init__(self, farm, client=None, model: str = MODEL, effort: str = EFFORT):
        self.farm = farm
        self._client = client
        self.model = model
        self.effort = effort

    @property
    def client(self):
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def run(self, prompt: str, allow_suggestions: bool) -> tuple[str, list[Suggestion]]:
        toolbox = Toolbox(self.farm, allow_suggestions)
        messages = [{"role": "user", "content": prompt}]
        for _ in range(MAX_TURNS):
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM,
                tools=toolbox.definitions,
                output_config={"effort": self.effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                messages=messages,
            )
            if response.stop_reason == "refusal":
                return "I can't help with that request.", toolbox.suggestions
            # Pass the whole content back unchanged (thinking blocks included).
            messages.append({"role": "assistant", "content": response.content})
            calls = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason != "tool_use" or not calls:
                text = "".join(b.text for b in response.content if b.type == "text").strip()
                return text, toolbox.suggestions
            results = []
            for call in calls:
                try:
                    out = toolbox.run(call.name, dict(call.input))
                    results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(out, ensure_ascii=False)})
                except ToolError as e:
                    results.append({"type": "tool_result", "tool_use_id": call.id, "content": str(e), "is_error": True})
                except Exception as e:  # API down, bad params: tell the model instead of crashing the loop
                    results.append({"type": "tool_result", "tool_use_id": call.id, "content": f"tool failed: {e}", "is_error": True})
            messages.append({"role": "user", "content": results})
        return "I stopped before finishing: the check took too many steps.", toolbox.suggestions

    def ask(self, question: str) -> str:
        """Read-only question, e.g. "how is the farm today?". Never creates suggestions."""
        text, _ = self.run(question, allow_suggestions=False)
        return text

    def daily_check(self) -> tuple[str, list[Suggestion]]:
        return self.run(DAILY_CHECK, allow_suggestions=True)
