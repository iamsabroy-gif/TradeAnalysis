"""
Supabase-backed result store.

Uses the synchronous ``supabase`` Python client (PostgREST over HTTPS), which is
a good fit for serverless functions — each request is a stateless HTTP call, so
there is no database connection pool to exhaust across cold starts.

Expected table (see supabase/migrations):

    create table public.phase1_results (
        result_id     text primary key,
        ticker        text not null,
        result        jsonb not null,
        company_input jsonb,
        created_at    timestamptz not null default now(),
        updated_at    timestamptz not null default now()
    );
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from supabase import Client, create_client

TABLE = "phase1_results"


class SupabaseResultStore:
    def __init__(self, url: str, key: str) -> None:
        self._client: Client = create_client(url, key)

    def save_result(
        self,
        result_id: str,
        ticker: str,
        result: Dict[str, Any],
        company_input: Dict[str, Any],
    ) -> None:
        self._client.table(TABLE).upsert(
            {
                "result_id": result_id,
                "ticker": ticker,
                "result": result,
                "company_input": company_input,
            },
            on_conflict="result_id",
        ).execute()

    def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        resp = (
            self._client.table(TABLE)
            .select("result, company_input")
            .eq("result_id", result_id)
            .limit(1)
            .execute()
        )
        data: Any = resp.data
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        first_row = data[0]
        if not isinstance(first_row, dict):
            return None
        return {
            "result": first_row.get("result"),
            "company_input": first_row.get("company_input"),
        }

    def latest_result_id_for_ticker(self, ticker: str) -> Optional[str]:
        resp = (
            self._client.table(TABLE)
            .select("result_id")
            .eq("ticker", ticker)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        data: Any = resp.data
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        first_row = data[0]
        if isinstance(first_row, dict):
            val = first_row.get("result_id")
            return str(val) if val is not None else None
        return None
