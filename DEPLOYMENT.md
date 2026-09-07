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

## Known limitations on serverless

- **In-memory stores are not durable.** `RESULTS_STORE`, `INPUTS_STORE`, and
  `TICKER_LATEST_MAP` in `main.py` live in process memory. On Vercel each
  invocation may hit a fresh/cold instance, so a `result_id` saved by one
  request may not be found by a later `GET /api/results/{id}`. For durable
  history, back these with an external store (e.g. Vercel KV / Postgres,
  Supabase, Redis). This does not affect single-request flows like
  `/api/evaluate` or `/api/tickers/{ticker}/run`, which return the report inline.
- **Screener scraping** (`/api/tickers/{ticker}/run`) makes outbound HTTP calls;
  keep an eye on the 60s function timeout set in `vercel.json` (`maxDuration`).
