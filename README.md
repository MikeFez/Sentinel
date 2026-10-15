# Sentinel

A self-hosted stock and company intelligence dashboard that aggregates news, stock prices, and key metrics with AI-powered analysis and sentiment tracking.

## Features

✅ **Phase 1 - Foundation**
- Company tracking with support for public, pre-IPO, private, and acquired companies
- Tag-based organization and color-coding
- Dark mode UI with modern design
- CRUD operations for companies and tags
- Sidebar navigation with grouped companies

✅ **Phase 2 - Sync & Data**
- Real-time stock data fetching (yfinance)
- News aggregation from Google News RSS
- Manual sync with comprehensive data collection
- Staleness alerts for outdated data
- Historical sync tracking

✅ **Phase 3 - AI Integration**
- LLM integration via any OpenAI-compatible endpoint
- Intelligent news summarization
- Sentiment analysis (bullish/bearish/neutral/mixed)
- Configurable AI models
- Context-aware financial insights

✅ **Phase 4 - Home Dashboard**
- Recent activity feed across all companies
- Stale company tracking with color-coded severity
- Enhanced overview cards
- Aggregated statistics and sentiment distribution

✅ **Phase 5 - Docker & Polish**
- Multi-stage Docker builds
- Docker Compose configuration
- Production-ready deployment
- Static file serving
- Data persistence with volume mounts

## Daily briefing, evidence, and evaluation

- **What changed?** on the dashboard combines material stories, new filing risks, sentiment changes,
  analysis changes, and earnings due within a week. Holdings and material developments receive priority.
  Mark entries reviewed, return them to the inbox, or set a reminder for 24 hours later. Review state is
  saved on the server and shared across browsers. Visiting a company does not mark its briefing reviewed.
  The briefing covers the past 30 days; a story updated after review returns as a new entry.
- **Evidence links** in new company, Research, and Discovery analyses connect summary paragraphs,
  key points, and risks to supplied articles, filings, and saved metric snapshots. The server accepts
  references only to sources supplied to that analysis. Sources remain saved when old sync detail is
  pruned. Unsupported claims are labeled; source references are not independent fact checking. Older
  analyses keep their original content without invented citations or prompt metadata.
- **AI scorecard** shows sample sizes, a descriptive 95% hit-rate interval, model/prompt cohorts, and
  SPY-relative returns alongside absolute returns. New analyses use an explicit 30-day outlook; the
  scorecard can evaluate 7, 30, and 90-day outcomes. SPY quotes are collected automatically with the
  normal quote refresh (requires Finnhub and a positive price refresh interval), without adding SPY to
  the watchlist. There is no historical backfill: relative results stay blank until matching prices
  exist. Returns exclude dividends and fees and are not adjusted for corporate actions.

## Tech Stack

- **Backend**: Python 3.12+ / FastAPI
- **Frontend**: React (TypeScript) + Vite
- **Database**: SQLite (via SQLAlchemy + Alembic)
- **AI**: Any OpenAI-compatible LLM endpoint (llama-swap, llama.cpp, vLLM, OpenAI, ...)
- **Stock Data**: yfinance
- **News Data**: Google News RSS
- **Deployment**: Docker + Docker Compose

## Getting Started

### Prerequisites

- Docker
- Docker Compose
- An OpenAI-compatible LLM endpoint

### Quick Start

The easiest way to get started:

```bash
# Start Sentinel
make start

# That's it! Visit http://localhost:8000
```

### Other Useful Commands

```bash
# View all available commands
make help

# View logs
make logs

# Check status
make status

# Stop
make stop

# Restart
make restart
```

### Manual Docker Commands

If you prefer not to use the Makefile:

```bash
# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Visit http://localhost:8000

See [DOCKER.md](DOCKER.md) for detailed Docker deployment guide.
See [MAKEFILE.md](MAKEFILE.md) for all available make commands.

## Published image

CI (`.gitea/workflows/build.yml`) builds and pushes on every push to `main`:

- `gitea.fessenden.app/mikefez/sentinel:latest`
- `gitea.fessenden.app/mikefez/sentinel:<commit sha>`

See `docker-compose.example.yml`. Pulling needs `docker login gitea.fessenden.app`.

| | |
|---|---|
| Port | `8000` |
| Volume | `/app/data` (SQLite database) |
| `FINNHUB_API_KEY` | Finnhub API key |
| `LLM_BASE_URL` | OpenAI-compatible base URL including `/v1`, e.g. `http://athena.lan:8090/v1` (default until changed in Settings) |
| `LLM_MODEL` | Model name, e.g. `qwen3.8:27b` (default until changed in Settings) |
| `LLM_API_KEY` | Optional bearer token for the endpoint (env only, never stored in the DB) |
| `LLM_MAX_TOKENS` | Output token budget per LLM call (default `16384`, until changed in Settings; `0` = the server's default). This is the reply only, not the context window: keep it below the server's per-slot context minus the prompt. Reasoning models need room to think before answering |
| `SEC_USER_AGENT` | Contact for SEC EDGAR requests, e.g. `Jane Doe jane@example.com` (SEC rejects anonymous clients) |
| `NOTIFY_URLS` | Where notifications go: one or more [Apprise URLs](https://github.com/caronc/apprise/wiki) (ntfy, Pushover, Discord, Telegram, email...), space-separated. Env only, since they hold tokens. Which events are sent is chosen in Settings |
| `SENTINEL_URL` | Sentinel's own address, e.g. `http://athena.lan:8000`, for links in notifications (optional) |
| `NEWS_ARTICLE_COUNT` | Articles per sync (initial default, `10`) |

## Project Structure

```
sentinel/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── routers/   # API endpoints
│   │   └── main.py    # FastAPI app
│   ├── alembic/       # Database migrations
│   └── requirements.txt
├── frontend/          # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── api/       # API client
│   │   ├── types/     # TypeScript types
│   │   └── styles/    # CSS files
│   └── package.json
└── data/              # SQLite database (created at runtime)
```

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

## Roadmap

- [x] Phase 1: Foundation (project scaffolding, CRUD operations, basic UI)
- [x] Phase 2: Sync & Data (stock data, news fetching, sync orchestration)
- [x] Phase 3: AI Integration (LLM, sentiment analysis)
- [x] Phase 4: Home Dashboard (aggregated views, activity feeds)
- [x] Phase 5: Polish & Docker (containerization, error handling)

## Future Enhancements

- Automatic scheduled syncs (cron-style, per company)
- IPO detection alerts for pre-IPO companies
- Market sector/category analysis
- Price target tracking
- Comparison view (side-by-side)
- Export reports (PDF/CSV)
- Webhook/notification support
- Historical price charts

## License

MIT + Commons Clause (see LICENSE file)

## Contributing

This is a personal project. Feel free to fork and modify for your own use.
