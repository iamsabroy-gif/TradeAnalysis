"""
Persistence layer for Phase 1 evaluation results.

Exposes a small `ResultStore` interface with two implementations:

* `InMemoryResultStore` — process-local dicts (default; used for local dev and
  tests, and as a fallback when Supabase is not configured).
* `SupabaseResultStore` — durable storage in Supabase Postgres over the REST
  (PostgREST) API, suitable for serverless deployments like Vercel where
  process memory does not persist across invocations.

`get_store()` returns a Supabase-backed store when `SUPABASE_URL` and a service
key are present in the environment, otherwise the in-memory store.
"""

from .store import (
    InMemoryResultStore,
    ResultStore,
    get_store,
    reset_store_cache,
)

__all__ = [
    "ResultStore",
    "InMemoryResultStore",
    "get_store",
    "reset_store_cache",
]
