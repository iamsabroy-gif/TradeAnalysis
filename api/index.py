"""
Vercel Python serverless entrypoint.

Vercel routes every request matching `/api/*` (see vercel.json rewrites) to this
file. It exposes the FastAPI ASGI `app`, which the Vercel Python runtime serves
directly. The original request path is preserved, so FastAPI's own `/api/...`
routes match unchanged.

If importing the application fails at cold start, we fall back to a tiny ASGI
app that returns the traceback in the HTTP response. That turns an opaque
`FUNCTION_INVOCATION_FAILED` into a readable error so the failure can be
diagnosed from the browser / curl.
"""

import os
import sys
import traceback

# Ensure the repository root is importable so `backend.*` resolves the same way
# it does when running locally from the project root.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from backend.app.api.main import app  # noqa: E402
except Exception:  # pragma: no cover - diagnostic fallback
    _TB = traceback.format_exc()
    _DIAG = (
        "Application failed to import at cold start.\n\n"
        + _TB
        + "\nsys.path:\n  "
        + "\n  ".join(sys.path)
        + "\n\nREPO_ROOT contents:\n  "
        + "\n  ".join(sorted(os.listdir(REPO_ROOT)))
    )
    print(_DIAG, file=sys.stderr)

    async def app(scope, receive, send):  # type: ignore[no-redef]
        if scope["type"] != "http":
            return
        body = _DIAG.encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 500,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": body})


__all__ = ["app"]
