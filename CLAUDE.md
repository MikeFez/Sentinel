# Sentinel – Claude Code Guide

## Architecture

Single-container Docker deployment:

- **Backend**: FastAPI (Python 3.12+), SQLAlchemy ORM, SQLite, Alembic migrations
- **Frontend**: React + TypeScript + Vite, built at container image time and served as static files by FastAPI
- **AI**: Ollama (external, configured via settings)
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
    services/          # Business logic (sync, stock, ollama, news)
  alembic/             # Database migrations
    versions/          # Migration scripts (committed)

frontend/
  src/
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

### Sync polling
Triggered syncs return a `202 Accepted` with a `Sync` record in `syncing` status. The frontend polls `GET /api/syncs/{id}` every 2 seconds until `status != "syncing"`, then reloads data.

### Database migrations
When adding columns to a model, write an Alembic migration in `backend/alembic/versions/`. Tables are also created via `Base.metadata.create_all()` on startup as a fallback, but migrations are the canonical path for schema changes.
