import asyncio
import httpx
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from .llm_service import LLMService
from .stock_service import StockService

from ..config import settings as app_settings_for_edgar
from . import activity, research_store

logger = logging.getLogger(__name__)

# Live sessions; each is also saved to Research history (research_store) as it progresses, and
# loaded back from there when it's no longer in memory (e.g. after a restart)
_sessions: dict[str, dict] = {}

_RUNNING = ("starting", "expanding", "searching", "validating")


def _persist(session: dict) -> None:
    research_store.save("discovery", session["theme"], session, item_id=session["session_id"])

_EDGAR_HEADERS = {
    "User-Agent": app_settings_for_edgar.sec_user_agent,
    "Accept": "application/json",
}


async def _edgar_get(client: httpx.AsyncClient, name: str, url: str, **kwargs) -> httpx.Response:
    """An EDGAR request, recorded on the Activity page."""
    with activity.track("sec", name) as t:
        resp = await client.get(url, **kwargs)
        if resp.status_code >= 400:
            t.fail(f"HTTP {resp.status_code}")
        return resp


def get_session(session_id: str) -> Optional[dict]:
    session = _sessions.get(session_id)
    if session is None:
        item = research_store.get(session_id)
        if item is None or item.kind != "discovery":
            return None
        session = item.data
        # Work in progress when the server stopped won't finish now
        if session.get("status") in _RUNNING:
            session["status"], session["error"] = "failed", "Interrupted by a server restart"
        for c in session.get("companies", []):
            if c.get("status") == "analyzing":
                c["status"] = "pending"
        _sessions[session_id] = session
    _persist(session)
    return session


def create_session(theme: str) -> dict:
    session_id = str(uuid.uuid4())
    session: dict = {
        "session_id": session_id,
        "theme": theme,
        "status": "starting",
        "error": None,
        "keywords": [],
        "etf_hints": [],
        "rationale": "",
        "companies": [],
        "progress": {"current": 0, "total": 0},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _sessions[session_id] = session
    _persist(session)
    return session


async def run_discover(
    session_id: str,
    llm_base_url: str,
    llm_model: str,
    finnhub_api_key: str,
    custom_instructions: str,
) -> None:
    """
    Full discovery pipeline. Mutates the session dict in place so the
    frontend can poll for incremental progress.
    """
    session = _sessions.get(session_id)
    if not session:
        return

    try:
        llm = LLMService(llm_base_url, llm_model)
        stock_service = StockService(finnhub_api_key)
        theme = session["theme"]

        # ── Step 1: Keyword expansion ───────────────────────────────────────
        session["status"] = "expanding"
        keywords, etf_hints, rationale = await _expand_keywords(llm, theme)
        session["keywords"] = keywords
        session["etf_hints"] = etf_hints
        session["rationale"] = rationale
        logger.info(f"[{session_id}] Expanded '{theme}' → {keywords}")

        # ── Step 2: SEC EDGAR full-text search ─────────────────────────────
        session["status"] = "searching"
        cik_companies = await _search_edgar(keywords)
        logger.info(f"[{session_id}] EDGAR returned {len(cik_companies)} candidate companies")

        if not cik_companies:
            session["status"] = "complete"
            return

        # ── Step 3: Resolve CIKs → tickers via SEC submissions API ─────────
        session["status"] = "validating"
        companies = await _resolve_tickers(cik_companies, stock_service)
        session["companies"] = companies
        session["progress"] = {"current": 0, "total": len(companies)}
        logger.info(f"[{session_id}] Resolved {len(companies)} tickers")

        if not companies:
            session["status"] = "complete"
            return

        session["status"] = "complete"

    except Exception as exc:
        logger.error(f"[{session_id}] Discovery failed: {exc}", exc_info=True)
        session["status"] = "failed"
        session["error"] = str(exc)
    finally:
        if session is not None:
            _persist(session)


async def analyze_one(
    session_id: str,
    ticker: str,
    llm_base_url: str,
    llm_model: str,
    finnhub_api_key: str,
    custom_instructions: str,
) -> None:
    """
    Run sentiment analysis for a single company within a session.
    Called on demand when the user clicks Analyze on a row.
    """
    session = _sessions.get(session_id)
    if not session:
        return

    company = next((c for c in session["companies"] if c["ticker"] == ticker), None)
    if not company:
        return

    try:
        llm = LLMService(llm_base_url, llm_model)
        stock_service = StockService(finnhub_api_key)
        await _analyze_company(company, llm, stock_service, custom_instructions)
    except Exception as exc:
        logger.error(f"[{session_id}] On-demand analysis failed for {ticker}: {exc}")
        company["status"] = "failed"
    finally:
        _persist(session)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _expand_keywords(llm: LLMService, theme: str) -> tuple[list, list, str]:
    """Ask the LLM to expand a free-text theme into SEC filing search terms."""
    prompt = f"""You are a financial research assistant.

Given the investment theme: "{theme}"

Return ONLY a valid JSON object — no explanation, no markdown, no code fences:
{{
  "search_terms": ["term1", "term2", "term3", "term4"],
  "etf_hints": ["ETF1"],
  "rationale": "One sentence describing what this theme covers."
}}

Rules:
- search_terms: 4-6 specific technical or industry keywords that companies operating in this space would use in their SEC 10-K annual reports. Use domain-specific jargon, not generic words like "technology" or "growth".
- etf_hints: tickers of well-known ETFs focused on this theme (empty array if none apply).
- rationale: one concise sentence describing the theme.
"""

    response = await llm.generate(prompt, timeout=180, purpose="theme keywords")
    if not response:
        return [theme], [], ""

    try:
        # Strip markdown fences if the model wrapped the output
        cleaned = re.sub(r"```(?:json)?", "", response).strip().rstrip("`")
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            data = json.loads(match.group())
            terms = data.get("search_terms") or [theme]
            return (
                [t for t in terms if isinstance(t, str) and t.strip()],
                [e for e in (data.get("etf_hints") or []) if isinstance(e, str)],
                data.get("rationale") or "",
            )
    except Exception as exc:
        logger.warning(f"Keyword expansion JSON parse failed: {exc} — raw: {response[:300]}")

    return [theme], [], ""


async def _search_edgar(keywords: list[str]) -> list[dict]:
    """
    Query SEC EDGAR full-text search for each keyword across recent 10-K filings.
    Returns a deduplicated list of {entity_name, cik, hit_count} dicts sorted by relevance.
    """
    cik_hits: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=20, headers=_EDGAR_HEADERS) as client:
        for keyword in keywords:
            try:
                resp = await _edgar_get(
                    client, "full-text search",
                    "https://efts.sec.gov/LATEST/search-index",
                    params={
                        "q": f'"{keyword}"',
                        "forms": "10-K",
                        "dateRange": "custom",
                        "startdt": "2022-01-01",
                        "hits.hits.total.value": "true",
                    },
                )
                if resp.status_code != 200:
                    logger.warning(f"EDGAR returned {resp.status_code} for '{keyword}'")
                    continue

                data = resp.json()
                for hit in data.get("hits", {}).get("hits", []):
                    src = hit.get("_source", {})
                    # EDGAR returns "ciks" as a list of zero-padded 10-digit strings
                    ciks = src.get("ciks") or []
                    if not ciks:
                        continue
                    cik = ciks[0]
                    # display_names format: "COMPANY NAME  (CIK 0000000000)"
                    display_names = src.get("display_names") or []
                    raw_name = display_names[0] if display_names else ""
                    name = raw_name.split("  (CIK")[0].strip() if raw_name else cik
                    if not name:
                        continue
                    if cik in cik_hits:
                        cik_hits[cik]["hit_count"] += 1
                    else:
                        cik_hits[cik] = {"entity_name": name, "cik": cik, "hit_count": 1}

            except Exception as exc:
                logger.warning(f"EDGAR search failed for '{keyword}': {exc}")

            # Be polite to SEC servers
            await asyncio.sleep(0.25)

    # Most cross-keyword hits first → strongest thematic relevance; cap at 15
    return sorted(cik_hits.values(), key=lambda x: x["hit_count"], reverse=True)[:15]


async def _resolve_tickers(cik_companies: list[dict], stock_service: StockService) -> list[dict]:
    """
    For each CIK, call data.sec.gov/submissions to get the exchange ticker.
    Then validate the ticker is still active by fetching a Finnhub quote.
    """
    resolved = []
    seen_tickers: set[str] = set()

    async with httpx.AsyncClient(timeout=12, headers=_EDGAR_HEADERS) as client:
        for company in cik_companies:
            # CIKs from EDGAR are already zero-padded to 10 digits
            cik_padded = company["cik"].zfill(10)
            try:
                resp = await _edgar_get(client, "submissions", f"https://data.sec.gov/submissions/CIK{cik_padded}.json")
                if resp.status_code != 200:
                    continue

                data = resp.json()
                tickers = data.get("tickers") or []
                if not tickers:
                    continue

                ticker = tickers[0].upper()
                if ticker in seen_tickers:
                    continue
                seen_tickers.add(ticker)

                name = data.get("name") or company["entity_name"]

                # Pull live quote from Finnhub to confirm the ticker is active
                stock_data = await asyncio.to_thread(stock_service.get_stock_data, ticker) or {}

                resolved.append({
                    "ticker": ticker,
                    "name": name,
                    "cik": company["cik"],
                    "edgar_hits": company["hit_count"],
                    "status": "pending",
                    "stock_price": stock_data.get("stock_price"),
                    "price_change": stock_data.get("price_change"),
                    "market_cap": stock_data.get("market_cap"),
                    "industry": stock_data.get("industry"),
                    "sentiment": None,
                    "summary": None,
                })

            except Exception as exc:
                logger.warning(f"Ticker resolution failed for CIK {cik_padded}: {exc}")

            await asyncio.sleep(0.1)

    return resolved


async def _analyze_company(
    company: dict,
    llm: LLMService,
    stock_service: StockService,
    custom_instructions: str,
) -> None:
    """Fetch recent news and run LLM analysis for a single company. Mutates company dict."""
    ticker = company["ticker"]

    news_articles, analyst_ratings, insider_transactions = await asyncio.gather(
        asyncio.to_thread(stock_service.get_company_news, ticker, 7),
        asyncio.to_thread(stock_service.get_analyst_recommendations, ticker),
        asyncio.to_thread(stock_service.get_insider_transactions, ticker),
    )

    stock_data: Optional[dict] = None
    if company.get("stock_price"):
        stock_data = {
            "stock_price": company["stock_price"],
            "price_change": company["price_change"],
            "market_cap": company["market_cap"],
        }

    from .evidence import source_catalog, validated_evidence
    from .llm_service import prompt_version
    sources = source_catalog(news_articles, stock_data, analyst_ratings)
    analysis, _ = await llm.analyze_company(
        company_name=company["name"],
        ticker=ticker,
        status="public",
        stock_data=stock_data,
        news_articles=news_articles,
        analyst_ratings=analyst_ratings,
        insider_transactions=insider_transactions,
        custom_instructions=custom_instructions or None,
        evidence_sources=sources,
    )
    if analysis is None:
        raise RuntimeError(llm.last_error or "AI analysis failed")

    company["sentiment"] = analysis.sentiment
    company["summary"] = analysis.summary
    company["evidence"] = validated_evidence(analysis, sources)
    company["prompt_version"] = prompt_version(custom_instructions, False)
    company["model"] = llm.model
    company["prediction_days"] = 30
    company["status"] = "complete"
