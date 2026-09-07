"""
Vercel Python serverless entrypoint.

Vercel routes every request matching `/api/*` (see vercel.json rewrites) to this
file. It exposes the FastAPI ASGI `app`, which the Vercel Python runtime serves
directly. The original request path is preserved, so FastAPI's own `/api/...`
routes match unchanged.
"""

import os
import sys

# Ensure the repository root is importable so `backend.*` and `tests.*` resolve
# the same way they do when running locally from the project root.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.api.main import app  # noqa: E402

# `app` is the ASGI callable Vercel's Python runtime looks for.
__all__ = ["app"]
