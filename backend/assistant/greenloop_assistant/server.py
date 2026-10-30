"""HTTP service: POST /api/assistant/chat and a minimal chat page at /.

Run: uvicorn greenloop_assistant.server:app --port 8010
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import llm, load_env
from .core import DEFAULT_CALENDAR, DEFAULT_KNOWLEDGE, Assistant, NotConfigured

load_env()

STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="GreenLoop farming assistant")
assistant = Assistant(
    Path(os.environ.get("KNOWLEDGE_DIR", DEFAULT_KNOWLEDGE)),
    Path(os.environ.get("CROP_CALENDAR", DEFAULT_CALENDAR)),
)


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@app.get("/")
def page():
    return FileResponse(STATIC / "index.html")


@app.get("/api/assistant/health")
def health():
    return {"ok": True, "notes": len(assistant.kb.notes), "calendar_rows": len(assistant.calendar.rows)}


@app.post("/api/assistant/chat")
def chat(body: ChatIn):
    auth_error, rate_limit_error, other_errors = llm.api_errors()
    try:
        answer = assistant.ask(body.question)
    except (NotConfigured, auth_error):
        raise HTTPException(503, "The assistant is not configured: set NVIDIA_API_KEY or ANTHROPIC_API_KEY in .env.")
    except rate_limit_error:
        raise HTTPException(429, "The assistant is busy. Try again in a minute.")
    except other_errors:
        raise HTTPException(502, "The assistant could not reach the language model. Try again.")
    return {"answer": answer.text, "sources": answer.sources}
