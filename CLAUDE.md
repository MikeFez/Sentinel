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
      sync_runner.py   # start_sync/run_sync: the only way syncs are started (API, "sync stale", auto-refresh)
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
- Start syncs only through `services/sync_runner.py` (`start_sync` + `run_sync`). It refuses a second sync for a company that already has one running, and at startup marks syncs left in `syncing` by a restart as failed.
- Finnhub calls are blocking (`httpx.Client` + `time.sleep` back-off): call them via `asyncio.to_thread` from async code, or they freeze the whole server.
- A sync is `failed` (with `error`) only when fetching data fails. If only the LLM fails, it is `completed` with the market data and `error = "AI analysis unavailable: ..."`; no sentiment is invented.
- `GET /api/companies` returns the newest *completed* sync as `latest_sync`, plus `is_syncing` and `sync_error` (newest sync failed). The UI shows the newest analysis that exists, which may be older than the newest data.
- `POST /api/companies/{id}/sync` returns `202` with the running sync. The frontend doesn't poll it directly: `AppData` polls the company list every 3 s while any company is syncing and toasts when one finishes.

### Times
Timestamps are stored as naive UTC (SQLite) via `UTCDateTime` in `database.py`, which reads them back as aware UTC, so the API sends `...Z`. Use `parseTime`/`ago` from `lib/format.ts` on the frontend, not `new Date(str)` math.

### Pages
Dashboard (`/`: portfolio, watchlist, needs-attention, earnings, latest analysis), company page (tabs: overview, news, insider trades, history), News, IPOs, Research (`/research?tab=analyze|discover`), Settings. `/portfolio`, `/analyze` and `/discover` redirect.

### Database migrations
When adding columns to a model, write an Alembic migration in `backend/alembic/versions/`. Tables are also created via `Base.metadata.create_all()` on startup as a fallback, but migrations are the canonical path for schema changes.
