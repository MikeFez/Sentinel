# Sentinel – Future Ideas

## Domain Discovery & Batch Analysis

**Concept**: Type in a theme or sector (e.g. "Water Desalination", "Nuclear Fusion", "AI Chips") and Sentinel automatically identifies relevant public companies, fetches stock/news data for each, and runs sentiment analysis — producing a ranked, side-by-side view of the space.

### Company Identification Strategy

The hard problem is turning a free-text theme into a reliable list of tickers without LLM hallucination. The best approach is a two-step pipeline:

**Step 1 — Keyword expansion via the LLM**

Ask the LLM to expand the user's theme into concrete search terms. Prompt it for structured JSON output:

```
Given the theme "Water Desalination", return a JSON object with:
- "search_terms": 4-6 specific technical/industry keywords to search SEC filings
  (e.g. ["reverse osmosis", "desalination", "water treatment", "brine management"])
- "etf_hints": any well-known ETFs or indices focused on this theme (e.g. "PHO", "FIW")
- "rationale": one sentence explaining the theme

Return only valid JSON, no commentary.
```

This avoids asking the LLM to invent tickers and instead uses it for what it's good at: semantic expansion.

**Step 2 — Company discovery via SEC EDGAR full-text search**

SEC EDGAR's full-text search API is free, requires no API key, and searches actual company filings (10-K, 10-Q, 8-K) since 2001. Companies that discuss a technology in their filings are genuinely operating in that space — not just tangentially related.

```
GET https://efts.sec.gov/LATEST/search-index?q="reverse+osmosis"&dateRange=custom&startdt=2023-01-01&forms=10-K
```

Returns hits with `entity_name`, `ticker`, `filed` date, and a text snippet showing context. Run one query per expanded keyword, deduplicate by ticker, rank by hit frequency across terms.

**Step 3 — Validation and enrichment via Finnhub**

For each candidate ticker, call Finnhub's company profile endpoint (already in `StockService`) to confirm it's still publicly traded and get current price, market cap, and sector. Filter out anything that doesn't resolve — this catches tickers that have been delisted or were misidentified.

**Step 4 — Batch sentiment analysis**

For each validated company, run the same news fetch + LLM analysis as a normal sync, but store results in a temporary session rather than persisting to the database.

---

### UI Sketch

New route: `/discover`

```
[ Water Desalination           ] [Discover →]

Identified 8 companies in "Water Desalination"  [Sort: Sentiment ▾]

┌──────────────────┬────────┬──────────┬───────────┬──────────────┬──────────────────────────────┬───────────┐
│ Company          │ Ticker │ Price    │ Today %   │ Market Cap   │ Sentiment                    │           │
├──────────────────┼────────┼──────────┼───────────┼──────────────┼──────────────────────────────┼───────────┤
│ Xylem Inc.       │ XYL    │ $112.40  │ +1.2%     │ $20.1B       │ 🟢 Bullish                   │ + Watch   │
│ Veolia Environ.  │ VEOEY  │ $14.90   │ -0.4%     │ $11.2B       │ 🟡 Neutral                   │ + Watch   │
│ ...              │        │          │           │              │                              │           │
└──────────────────┴────────┴──────────┴───────────┴──────────────┴──────────────────────────────┴───────────┘

[ Show AI summary for each row on hover / expand ]
```

Clicking a row expands the AI summary inline. "+ Watch" creates the company record and navigates to its detail page (same as the IPO calendar's "Watch" button).

---

### Implementation Notes

- **Results are ephemeral** — nothing is persisted until the user clicks "+ Watch"
- **Rate limiting** — Finnhub and LLM calls must be sequential, not parallel. Use the existing exponential backoff in `StockService._request()`. With 8 companies, expect ~2–3 minutes total.
- **Progress feedback** — stream status updates to the frontend as each company is processed (SSE or simple polling against a session key). Show a progress bar or per-company status chips.
- **EDGAR pagination** — each keyword search returns up to 10 results by default; use `&from=0&size=20` to get more. Deduplicate aggressively — the same company may appear across multiple keyword searches.
- **ETF seeding (optional enhancement)** — if the LLM returns ETF hints (e.g. `PHO`), Finnhub's ETF holdings endpoint can return constituent tickers as a high-quality seed list, supplementing the EDGAR approach.
- **SEC EDGAR rate limits** — the public API is rate-limited to ~10 requests/second; with 4–6 keyword queries this is not a concern.
- **No new API keys required** for the core flow — SEC EDGAR is free and unauthenticated; Finnhub is already integrated.

---

## Other Ideas

### Comparison View
Side-by-side panel for 2–3 companies: price chart, sentiment trend, analyst ratings, and key metrics aligned in columns. Useful when evaluating alternatives in the same space.

### Price History Chart
Line chart of `stock_price` across all completed syncs for a company. Already have the data — just needs a charting component (Recharts is already in the bundle).

### Email / Webhook Alerts
When a price alert fires or a sentiment flips (e.g. bullish → bearish), send a notification via email (SMTP) or a webhook (Slack, Discord, ntfy). Would pair with the auto-refresh loop as the trigger.

### Watchlist Notes
Free-text notes field per company, visible on the detail page. Useful for recording thesis, concerns, or reminders. Could also be injected into the LLM prompt as extra context (the ad-hoc analysis page already supports this pattern).

### Tag-Based Filtering on Dashboard
Filter the company list by tag on the homepage, not just by search. Clicking a tag chip in the sidebar or header would narrow the list to that tag.

### Export
CSV or JSON export of all companies and their latest sync data — price, sentiment, analyst consensus, market cap. Useful for dropping into a spreadsheet.

### Sentiment History Chart
Visual sparkline (already exists) expanded into a full chart on the company detail page, showing sentiment and price together over time to correlate news cycles with price movement.
