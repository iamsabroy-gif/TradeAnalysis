# Deploying TradeAnalysis

Two supported free-tier targets:

- **[Render](#deploying-to-render-free-tier)** — a single persistent web service
  (no serverless function timeout; best for the screener scraping flow).
- **[Vercel](#deploying-tradeanalysis-to-vercel)** — serverless, one project.

---

# Deploying to Render (free tier)

Render runs the FastAPI app as a **single persistent Web Service** on the free
plan. FastAPI serves the API at `/api/*` and the pre-built Vite frontend
(`frontend/dist/`) at `/` from the same domain, so there are no CORS concerns and
no frontend changes. Unlike serverless, the process stays warm while in use and
long scrapes aren't bound by a function timeout.

Everything is declared in [`render.yaml`](render.yaml) (a Render Blueprint).

## Deploy via the Render dashboard (recommended)

1. Push this branch to GitHub.
2. Go to <https://dashboard.render.com/> → **New** → **Blueprint**.
3. Connect the `iamsabroy-gif/tradeanalysis` repository. Render reads
   `render.yaml` and proposes a free Web Service named `tradeanalysis`:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.app.api.main:app --host 0.0.0.0 --port $PORT`
   - Health Check Path: `/api/health`
4. (Optional persistence) Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
   in the service's **Environment** tab — see
   [Persistence](#persistence-supabase) below. Leave them unset to run with
   in-memory storage.
5. Click **Apply** / **Create**. The first build installs Python deps and starts
   uvicorn.

## Verifying

- App UI: `https://tradeanalysis.onrender.com/` (your service's URL)
- API health: `https://<service>.onrender.com/api/health` → `{"status":"ok",...}`

## Notes and free-tier limits

- **Idle sleep:** free Web Services spin down after ~15 minutes of no traffic and
  cold-start (~30–60s) on the next request. Paid plans remove this.
- **No Node build step:** `frontend/dist/` is committed, so the Render build is
  Python-only. If you change frontend source, rebuild and commit:
  `cd frontend && npm install && npm run build`.
- **Persistence:** without Supabase env vars the in-memory store resets on every
  restart/sleep; set the two Supabase variables for durable results.

---

# Deploying TradeAnalysis to Vercel

This project deploys as a **single Vercel project**:

- **Frontend** — the Vite/React app in `frontend/` is built to static files and served from the CDN.
- **Backend** — the FastAPI app (`backend/app/api/main.py`) runs as a Python
  serverless function via `api/index.py`. Every request to `/api/*` is rewritten
  to that function, and FastAPI's own `/api/...` routes handle it.

Because the frontend already calls the API with relative `/api/*` URLs, both
halves share one domain and no frontend code changes are needed.

## Files that make this work

| File | Purpose |
| --- | --- |
| `vercel.json` | Build command, static output dir, `/api/*` → serverless rewrite, and `includeFiles` so the function bundle can import `backend/` and `tests/`. |
| `api/index.py` | Serverless entrypoint that exposes the FastAPI ASGI `app`. |
| `requirements.txt` | Python dependencies Vercel installs for the function. |
| `.vercelignore` | Keeps `.venv/`, `node_modules/`, caches out of the upload. |

## Option A — Deploy from the Vercel dashboard (recommended)

1. Push this branch to GitHub (already done if you're reading this after the commit).
2. Go to <https://vercel.com/new> and **Import** the `iamsabroy-gif/tradeanalysis` repository.
3. Vercel auto-detects `vercel.json`. Leave the settings as-is:
   - Build Command: `cd frontend && npm install && npm run build` (from `vercel.json`)
   - Output Directory: `frontend/dist` (from `vercel.json`)
4. Click **Deploy**. The first build installs both npm and Python deps.

## Option B — Deploy from the CLI

```bash
npm i -g vercel     # install the CLI once
vercel login        # authenticate
vercel              # preview deploy (follow the prompts)
vercel --prod       # promote to production
```

Run these from the repository root (where `vercel.json` lives).

## Verifying a deployment

- App UI: `https://<your-project>.vercel.app/`
- API health: `https://<your-project>.vercel.app/api/health` → `{"status":"ok",...}`

## Persistence (Supabase)

Evaluation results are persisted through a small store abstraction in
`backend/app/persistence/`:

- When `SUPABASE_URL` and a service key are set in the environment, the backend
  uses **Supabase Postgres** (`SupabaseResultStore`, over the REST API) — durable
  across serverless invocations.
- Otherwise it falls back to a **process-local in-memory store** — used for local
  dev and tests, and (as a degraded mode) if Supabase is unreachable.

### Required environment variables (set these in Vercel → Project → Settings → Environment Variables)

| Variable | Value |
| --- | --- |
| `SUPABASE_URL` | `https://gzuibxcoeevnmnvbezpm.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | The **service_role** secret from Supabase → Project Settings → API Keys. Server-side only — never expose it to the frontend. |

The `phase1_results` table uses Row Level Security with no public policies, so the
data is reachable only with the service role key (which bypasses RLS). The anon /
publishable key cannot read it. The `SUPABASE_URL` above points at the
`iamsabroy@gmail.com's Project` Supabase project; the table was created by
`supabase/migrations/0001_phase1_results.sql`.

For local development, export the same two variables in your shell before
starting `uvicorn`; leave them unset to use in-memory storage.

## Known limitations on serverless

- **Screener scraping** (`/api/tickers/{ticker}/run`) makes outbound HTTP calls;
  keep an eye on the 60s function timeout set in `vercel.json` (`maxDuration`).
- With Supabase configured, evaluation history persists. Without it (no env
  vars), a `result_id` saved by one request may not be found by a later
  `GET /api/results/{id}` because each serverless invocation can be a fresh
  instance. Single-request flows (`/api/evaluate`, `/api/tickers/{ticker}/run`)
  return the report inline and are unaffected either way.
