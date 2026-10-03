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
| `SEC_USER_AGENT` | Contact for SEC EDGAR requests, e.g. `Jane Doe jane@example.com` (SEC rejects anonymous clients) |
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
