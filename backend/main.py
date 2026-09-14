"""Vercel entrypoint for Nyaya Sahayak FastAPI backend."""

import sys
from pathlib import Path

# Ensure backend root and app directory are in sys.path
backend_dir = Path(__file__).resolve().parent
app_dir = backend_dir / "app"

for path in (str(backend_dir), str(app_dir)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.main import app  # noqa: E402

__all__ = ["app"]
