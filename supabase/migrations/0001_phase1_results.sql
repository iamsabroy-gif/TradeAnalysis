-- Phase 1 Gatekeeper: durable storage for evaluation results.
--
-- Each row is one evaluation revision, keyed by its result_id. The full
-- Phase1Result and originating CompanyInput are stored as JSONB so the schema
-- tracks the Pydantic models without migrations on every field change.

create table if not exists public.phase1_results (
    result_id     text primary key,
    ticker        text not null,
    result        jsonb not null,
    company_input jsonb,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);

-- Fast "latest evaluation for a ticker" lookups.
create index if not exists phase1_results_ticker_created_at_idx
    on public.phase1_results (ticker, created_at desc);

-- Keep updated_at fresh on upsert/update.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists phase1_results_set_updated_at on public.phase1_results;
create trigger phase1_results_set_updated_at
    before update on public.phase1_results
    for each row
    execute function public.set_updated_at();

-- Row Level Security: enabled with no public policies. The backend connects
-- with the service role key, which bypasses RLS, so data is not reachable via
-- the anon/publishable key.
alter table public.phase1_results enable row level security;
