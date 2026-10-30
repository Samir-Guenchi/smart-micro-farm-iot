"""Vercel entry point for the farming assistant (FastAPI as one serverless function).

Vercel project for the assistant: Root Directory = repository root. See docs/deploy-vercel.md.
The code lives in backend/assistant/; this file stays here only because Vercel looks for
functions in api/ at the Root Directory, and the assistant also reads the shared knowledge/ and data/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "assistant"))

from greenloop_assistant.server import app  # noqa: E402,F401
