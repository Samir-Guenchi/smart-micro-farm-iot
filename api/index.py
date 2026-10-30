"""Vercel entry point for the farming assistant (FastAPI as one serverless function).

Vercel project for the assistant: Root Directory = repository root. See docs/deploy-vercel.md.
It needs the whole repo because the assistant reads knowledge/ and data/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "assistant"))

from greenloop_assistant.server import app  # noqa: E402,F401
