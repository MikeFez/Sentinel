# Sentinel – Claude Code Guide

## Architecture

Single-container Docker deployment:

- **Backend**: FastAPI (Python 3.12+), SQLAlchemy ORM, SQLite, Alembic migrations
- **Frontend**: React + TypeScript + Vite, built at container image time and served as static files by FastAPI
- **AI**: OpenAI-compatible LLM endpoint (external; `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`, URL and model overridable in Settings)
- **Stock data**: Finnhub API (key in `.env`)

The frontend is compiled into the image during `docker build`. There is no live-reload in production — any frontend or backend change requires a rebuild.

## Rebuilding

After making any code change (frontend or backend), run:

```
make docker-rebuild
```

This runs `docker-compose down && docker-compose build && docker-compose up -d` and the app will be available at http://localhost:8000.

Other useful commands:

```
make docker-logs  # tail container logs
make status       # check container and DB state
make db-backup    # snapshot the SQLite DB before risky changes
make db-reset     # wipe and reinitialize the database (destructive)
```

## Project layout

```
backend/
  app/
    config.py          # Pydantic Settings — single source of truth for defaults
    main.py            # FastAPI app, CORS, lifespan, auto-refresh background loop
    database.py        # SQLAlchemy engine + SessionLocal
    models/            # SQLAlchemy ORM models
    schemas/           # Pydantic request/response schemas
    routers/           # API route handlers
    services/          # Business logic (sync, stock, llm, news)
      sync_runner.py   # start_sync/run_sync: the only way syncs are started; Thresholds = staleness rules
      quote_service.py # price-only refresh while the US market is open (+ once after close)
      maintenance.py   # prune_history: drop bulky detail from old syncs and old news (daily)
      events.py        # syncs triggered by big price moves or earnings results
      news_store.py    # news articles stored once per company (news_articles table)
  tests/               # pytest suite: `make test`
  alembic/             # Database migrations
    versions/          # Migration scripts (committed)

frontend/
  src/
    state/AppData.tsx  # Shared company/tag list (polled; fast while anything syncs) + toasts
    lib/format.ts      # Money, %, relative times; parseTime() for server timestamps
    api/client.ts      # All API calls in one place
    types/index.ts     # TypeScript interfaces mirroring backend schemas
    components/        # React components
    styles/globals.css # Global CSS variables and base styles
```

## Key conventions

### Settings / defaults
All configurable defaults live in `backend/app/config.py` as a Pydantic `Settings` class. The `SETTING_DEFAULTS` dict in `routers/settings.py` is built from those values — do not hardcode defaults in two places.

### CSS
Global styles use plain CSS (no modules). Specificity collisions have bitten us before — scope rules to their component's root class (e.g., `.company-item .company-name`, not `.company-name` alone).

### Background sync
`main.py` runs `_auto_refresh_loop()` as a lifespan task. It wakes every 5 minutes and syncs stale **public companies with tickers** only. Non-public companies show the staleness indicator but are never auto-synced.

### Syncs
- Start syncs only through `queue_sync` in `services/sync_runner.py`. One worker runs them one at a time: manual first, then owned companies, then the rest (a manual request moves a queued sync to the front). It reuses a company's queued or running sync. `syncs.started_at` tells running from queued: at startup, queued ones are re-queued and running ones are marked failed and retried. `run_sync` never raises.
- `services/sync_progress.py` tracks the running sync's steps in memory (`sync_progress` on `GET /api/companies`; none = queued).
- Finnhub calls are blocking (`httpx.Client` + `time.sleep` back-off): call them via `asyncio.to_thread` from async code, or they freeze the whole server.
- A sync is `failed` (with `error`) only when fetching data fails. If only the LLM fails, it is `completed` with the market data and `error = "AI analysis unavailable: ..."`; no sentiment is invented.
- `GET /api/companies` returns the newest *completed* sync as `latest_sync`, plus `is_syncing` and `sync_error` (newest sync failed). The UI shows the newest analysis that exists, which may be older than the newest data.
- `POST /api/companies/{id}/sync` returns `202` with the running sync. The frontend doesn't poll it directly: `AppData` polls the company list every 3 s while any company is syncing and toasts when one finishes.

### AI analysis
The model is asked for one JSON object (summary, sentiment, key_points, risks, changes); `parse_analysis` in `llm_service.py` falls back to the old `SUMMARY:`/`SENTIMENT:` text. The prompt includes the previous analysis so `changes` can say what's different. The `ai_prompt_instructions` setting is guidance only; `clean_instructions` strips an old format section from saved values.

### Prices and staleness
- `companies.quote_*` holds the latest quote (every `price_refresh_minutes` during market hours). The frontend's `livePrice()` picks the quote or the last sync's price, whichever is newer; use it instead of `latest_sync.stock_price`.
- Public companies go stale after `staleness_hours` (auto-refresh: `auto_refresh_hours`); private/pre-IPO ones after `private_refresh_days`. All of this lives in `Thresholds`.

### Times
Timestamps are stored as naive UTC (SQLite) via `UTCDateTime` in `database.py`, which reads them back as aware UTC, so the API sends `...Z`. Use `parseTime`/`ago` from `lib/format.ts` on the frontend, not `new Date(str)` math.

### SQLite
The database runs in WAL mode with a 30 s busy timeout (`database.py`), so reads don't block on a sync's writes. Don't hold a write transaction across network calls (fetch first, then write), and end read transactions before slow work. `make db-backup` uses SQLite's online backup, since recent writes may still be in `sentinel.db-wal`.

### Event syncs and news
- Besides scheduled refreshes, the auto-refresh loop syncs a public company when its price moves `move_sync_percent` in a day (once per session) or after an earnings date's results are out. `syncs.reason` records why each sync ran.
- News lives in `news_articles` (deduplicated by URL per company); the News page and the company News tab read from it, not from `syncs.raw_news`.
- `stock_service.finnhub_status` holds the outcome of the last Finnhub request; Settings and the dashboard show it.
- Analyst rating shifts and large insider trades (`due_signal_syncs` in `events.py`) are checked once a day per public company and also trigger syncs.
- Peers come from the latest sync (`syncs.peers`); `GET /api/companies/{id}/peers` adds names and prices, cached for a day.
- `GET /api/export` / `POST /api/import` move companies, tags and settings as JSON (merge by ticker or name, never delete; `dry_run` previews).
- Research results (ad-hoc analyses, theme discoveries) are saved in `research_items` (`services/research_store.py`); discover sessions are loaded back from there after a restart.

### Scorecard, debate, filings, stories
- `services/scorecard.py` grades each day's last sentiment call per company against the price nearest to call + horizon (±25%), from `daily_prices` (one price per New York day, written by quote refreshes and syncs via `price_history.record_price`), sync prices and the latest quote. Calls with no price near their date are `no_data`, not pending. `syncs.llm_model` records the model.
- `analysis_mode = debate` makes three LLM calls (bull, bear, verdict). They, like all LLM calls, go through the shared semaphore (see Observability). `llm_reasoning_effort` is passed through as `reasoning_effort` when set.
- `services/filings.py` reads EDGAR (needs `SEC_USER_AGENT` with a contact or SEC returns 403), summarizes new 8-K/10-Q/10-K filings daily, and for 10-Ks diffs Risk Factors paragraphs against the previous 10-K in code before asking the LLM. Unsummarized filings aren't saved, so they're retried.
- `services/stories.py` groups each sync's new articles into `news_stories` (one LLM call), marks material ones, and tags themes (material stories only). Material stories and filing summaries go into the analysis prompt via `SyncService.extra_context`.

### Notifications
- `services/notifier.py` sends through Apprise to `NOTIFY_URLS` (env only: the URLs hold tokens). Each event has a `key`; the `notifications` table records what was sent, so report an event as often as you see it and it goes out once.
- Hooks: `after_quote` (price alerts on crossing, big moves) in the quote refresh, `after_sync` (sentiment flips, earnings, material stories, problems) after every sync, `after_filing` for non-routine filings, `maybe_send_digest` in the auto-refresh loop. Each `notify_<kind>` setting switches one kind off. Sending never raises.

### Observability
- `services/activity.py`: wrap outbound calls, syncs and jobs in `activity.track(kind, name)`; it records an `activity_events` row (kept 14 days) and Prometheus metrics (`/metrics`). `activity.context(company_id=...)` labels everything inside, across awaits and `asyncio.to_thread`. Recording never raises.
- LLM calls take a `purpose` (shown on the Activity page). All of Sentinel's LLM calls share one semaphore (`llm_max_concurrent`, default 1) so the shared LLM server keeps capacity for other users.
- API requests are counted in memory by a middleware (not stored).

### Tests and checks
`make test` runs `backend/tests` with uv against a throwaway SQLite database. Add a test when changing sync, staleness, parsing, event or pruning logic. The Docker build runs the backend tests and `npm run lint` + `tsc`, so CI fails (and nothing is published) if any of them fail.

### Pages
Dashboard (`/`: portfolio, watchlist, needs-attention, earnings, latest analysis), company page (tabs: overview, news, insider trades, history), News, IPOs, Research (`/research?tab=analyze|discover`), Settings. `/portfolio`, `/analyze` and `/discover` redirect.

### Database migrations
Alembic is the only thing that changes the schema. `docker-entrypoint.sh` runs `alembic upgrade head` and exits if it fails; the app never calls `create_all()` (only the tests do).
- The chain starts at `0001_initial` (the base tables), so a brand-new database migrates normally.
- Every migration must be safe to re-run: use `add_column` / `drop_column` / `has_table` from `app/migration_utils.py` instead of bare `op.add_column`, because older databases may already have some columns (the old entrypoint built tables without recording a version).
- `tests/test_migrations.py` checks a new database, one built without migrations, a half-migrated one, and an existing one against the models. Add data-carrying cases there when a migration moves data.
