"""GreenLoop farm agent v1: reads farm data, suggests actions, the farmer approves."""

import os
from pathlib import Path


def load_env(path: Path | None = None) -> None:
    """Read KEY=value lines from agent/.env (if present) without overriding real env vars."""
    path = path or Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))
