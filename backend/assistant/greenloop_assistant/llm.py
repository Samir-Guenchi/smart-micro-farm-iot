"""Pick the language model provider: Claude (Anthropic) or NVIDIA's OpenAI-compatible API.

The assistant and agent speak the Anthropic Messages shape. For NVIDIA, NvidiaClient
translates that shape to OpenAI chat completions and back, so their code and
tests stay the same whichever provider runs.

  LLM_PROVIDER     anthropic | nvidia. Default: nvidia when NVIDIA_API_KEY is set
                   and ANTHROPIC_API_KEY is not, otherwise anthropic.
  NVIDIA_API_KEY   key from build.nvidia.com (never commit it)
  NVIDIA_MODEL     default meta/llama-3.3-70b-instruct
  NVIDIA_BASE_URL  default https://integrate.api.nvidia.com/v1

This file is mirrored in backend/agent/greenloop_agent/llm.py; keep both in sync.
"""
from __future__ import annotations

import json
import os
import re
from types import SimpleNamespace

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"
# Open models on NVIDIA usually allow fewer output tokens than Claude.
NVIDIA_MAX_TOKENS = 4096

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


class NotConfigured(RuntimeError):
    """No credentials for the selected provider."""


def provider() -> str:
    chosen = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if chosen:
        return chosen
    if os.environ.get("NVIDIA_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        return "nvidia"
    return "anthropic"


def model_for(default_claude_model: str) -> str:
    """The model name to send: NVIDIA_MODEL for nvidia, else the Claude model."""
    if provider() == "nvidia":
        return os.environ.get("NVIDIA_MODEL", NVIDIA_MODEL)
    return default_claude_model


def make_client():
    if provider() == "nvidia":
        return NvidiaClient()
    import anthropic

    return anthropic.Anthropic()


def api_errors():
    """(auth, rate_limit, other) exception classes for the active provider, for HTTP error mapping."""
    if provider() == "nvidia":
        import openai

        return openai.AuthenticationError, openai.RateLimitError, (openai.APIStatusError, openai.APIConnectionError)
    import anthropic

    return anthropic.AuthenticationError, anthropic.RateLimitError, (anthropic.APIStatusError, anthropic.APIConnectionError)


class NvidiaClient:
    """Exposes client.beta.messages.create(**anthropic_kwargs) on top of an OpenAI-compatible API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, openai_client=None):
        self._openai = openai_client
        if self._openai is None:
            key = api_key or os.environ.get("NVIDIA_API_KEY")
            if not key:
                raise NotConfigured("LLM_PROVIDER is nvidia but NVIDIA_API_KEY is not set")
            from openai import OpenAI

            self._openai = OpenAI(api_key=key, base_url=base_url or os.environ.get("NVIDIA_BASE_URL", NVIDIA_BASE_URL))
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))
        self.messages = self.beta.messages

    def create(self, *, model, messages, max_tokens=NVIDIA_MAX_TOKENS, system=None, tools=None, **_ignored):
        # output_config, betas and fallbacks are Claude-only and are dropped here.
        kwargs = {
            "model": model,
            "messages": to_openai_messages(system, messages),
            "max_tokens": min(max_tokens, int(os.environ.get("NVIDIA_MAX_TOKENS", NVIDIA_MAX_TOKENS))),
            "temperature": 0.2,
        }
        if tools:
            kwargs["tools"] = [
                {"type": "function", "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t["input_schema"]}}
                for t in tools
            ]
        return from_openai_response(self._openai.chat.completions.create(**kwargs))


def _field(block, name, default=None):
    return block.get(name, default) if isinstance(block, dict) else getattr(block, name, default)


def to_openai_messages(system, messages) -> list[dict]:
    out = [{"role": "system", "content": system}] if system else []
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            out.append({"role": m["role"], "content": content})
            continue
        if m["role"] == "assistant":
            text = "".join(_field(b, "text", "") for b in content if _field(b, "type") == "text")
            calls = [
                {"id": _field(b, "id"), "type": "function", "function": {"name": _field(b, "name"), "arguments": json.dumps(_field(b, "input") or {}, ensure_ascii=False)}}
                for b in content
                if _field(b, "type") == "tool_use"
            ]
            msg = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
            continue
        texts = []
        for b in content:
            if _field(b, "type") == "tool_result":
                result = _field(b, "content", "")
                if _field(b, "is_error"):
                    result = f"Error: {result}"
                out.append({"role": "tool", "tool_call_id": _field(b, "tool_use_id"), "content": result})
            elif _field(b, "type") == "text":
                texts.append(_field(b, "text", ""))
        if texts:
            out.append({"role": "user", "content": "\n".join(texts)})
    return out


def from_openai_response(resp) -> SimpleNamespace:
    choice = resp.choices[0]
    msg = choice.message
    content = []
    text = _THINK.sub("", msg.content or "").strip()
    if text:
        content.append(SimpleNamespace(type="text", text=text))
    for call in msg.tool_calls or []:
        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        content.append(SimpleNamespace(type="tool_use", id=call.id, name=call.function.name, input=args))
    if any(b.type == "tool_use" for b in content):
        stop = "tool_use"
    elif choice.finish_reason == "length":
        stop = "max_tokens"
    else:
        stop = "end_turn"
    return SimpleNamespace(stop_reason=stop, content=content)
