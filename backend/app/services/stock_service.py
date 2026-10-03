import time
import httpx
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 5
_BACKOFF_BASE = 1.0   # seconds; doubles each retry, caps at 32s


# The outcome of the most recent Finnhub request, for the status shown in Settings and the dashboard
finnhub_status: Dict[str, Any] = {"ok": None, "error": None, "at": None}


def _record(ok: bool, error: Optional[str] = None) -> None:
    from datetime import datetime, timezone

    finnhub_status.update(ok=ok, error=error, at=datetime.now(timezone.utc))


class StockService:
    """Service for fetching stock data using Finnhub API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"

    def _request(self, url: str, params: Dict[str, Any], timeout: int = 10) -> Any:
        """
        GET a Finnhub endpoint with exponential backoff on 429 / 5xx.
        Raises httpx.HTTPStatusError on non-retryable failures.
        """
        delay = _BACKOFF_BASE
        for attempt in range(_MAX_RETRIES):
            try:
                with httpx.Client() as client:
                    response = client.get(url, params=params, timeout=timeout)
            except httpx.HTTPError as e:
                _record(False, f"Could not reach Finnhub: {e}")
                raise

            if response.status_code not in _RETRY_STATUSES:
                if response.status_code == 401:  # 403 just means an endpoint isn't in the plan
                    _record(False, "Finnhub rejected the API key (check FINNHUB_API_KEY)")
                elif response.is_success:
                    _record(True)
                response.raise_for_status()
                return response.json()

            if attempt < _MAX_RETRIES - 1:
                wait = min(delay, 32.0)
                logger.warning(
                    f"Finnhub returned {response.status_code} for {url} "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES}), retrying in {wait:.0f}s"
                )
                time.sleep(wait)
                delay *= 2
            else:
                _record(False, f"Finnhub kept returning HTTP {response.status_code}"
                        + (" (rate limited: the free plan allows 60 calls a minute)" if response.status_code == 429 else ""))
                response.raise_for_status()

        raise RuntimeError("Unreachable")

    def get_stock_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch stock data for a given ticker symbol using Finnhub API.

        Returns:
            Dictionary with stock data or None if ticker is invalid
        """
        if not self.api_key:
            logger.error("Finnhub API key not configured")
            return None

        try:
            # Fetch quote data (price, change, etc.)
            quote = self._fetch_quote(ticker)
            if not quote:
                return None

            # Fetch company profile (market cap, etc.)
            profile = self._fetch_profile(ticker)

            # Get current price
            current_price = quote.get("c")  # current price
            if not current_price:
                logger.warning(f"No price data found for ticker: {ticker}")
                return None

            # Calculate price change percentage
            price_change = quote.get("dp")  # percent change

            # Format market cap from profile
            market_cap_str = None
            if profile:
                market_cap = profile.get("marketCapitalization")
                if market_cap:
                    # Finnhub returns market cap in millions
                    market_cap_millions = market_cap
                    if market_cap_millions >= 1_000_000:
                        market_cap_str = f"${market_cap_millions / 1_000_000:.2f}T"
                    elif market_cap_millions >= 1_000:
                        market_cap_str = f"${market_cap_millions / 1_000:.2f}B"
                    else:
                        market_cap_str = f"${market_cap_millions:.2f}M"

            # Get 52-week high/low from metrics endpoint
            fifty_two_wk_hi = None
            fifty_two_wk_lo = None
            metrics = self._fetch_metrics(ticker)
            if metrics:
                fifty_two_wk_hi = metrics.get("52WeekHigh")
                fifty_two_wk_lo = metrics.get("52WeekLow")

            return {
                "stock_price": current_price,
                "price_change": price_change,
                "market_cap": market_cap_str,
                "pe_ratio": None,  # Finnhub doesn't provide this in quote
                "volume": quote.get("v"),  # volume
                "fifty_two_wk_hi": fifty_two_wk_hi,
                "fifty_two_wk_lo": fifty_two_wk_lo,
                "industry": profile.get("finnhubIndustry") if profile else None,
            }

        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {str(e)}")
            return None

    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Just the price and day change, e.g. {"price": 73.92, "change": 4.91}; None if unavailable."""
        if not self.api_key:
            return None
        quote = self._fetch_quote(ticker)
        if not quote or not quote.get("c"):
            return None
        return {"price": quote["c"], "change": quote.get("dp")}

    def _fetch_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch quote data from Finnhub"""
        try:
            url = f"{self.base_url}/quote"
            params = {"symbol": ticker, "token": self.api_key}
            data = self._request(url, params)

            # Check if we got valid data
            if data.get("c") == 0 and data.get("d") == 0:
                logger.warning(f"No quote data found for ticker: {ticker}")
                return None

            return data

        except Exception as e:
            logger.error(f"Error fetching quote for {ticker}: {str(e)}")
            return None

    def _fetch_profile(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch company profile from Finnhub"""
        try:
            url = f"{self.base_url}/stock/profile2"
            params = {"symbol": ticker, "token": self.api_key}
            data = self._request(url, params)

            if not data:
                logger.warning(f"No profile data found for ticker: {ticker}")
                return None

            return data

        except Exception as e:
            logger.error(f"Error fetching profile for {ticker}: {str(e)}")
            return None

    def _fetch_metrics(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch stock metrics from Finnhub (includes 52-week high/low)"""
        try:
            url = f"{self.base_url}/stock/metric"
            params = {"symbol": ticker, "metric": "price", "token": self.api_key}
            data = self._request(url, params)

            # Return the metric object which contains 52-week data
            return data.get("metric", {})

        except Exception as e:
            logger.error(f"Error fetching metrics for {ticker}: {str(e)}")
            return None

    def get_company_news(self, ticker: str, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch company-specific news from Finnhub

        Args:
            ticker: Stock symbol
            days: Number of days back to fetch news (default 7)

        Returns:
            List of news articles
        """
        if not self.api_key:
            logger.error("Finnhub API key not configured")
            return []

        try:
            from datetime import datetime, timedelta

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            url = f"{self.base_url}/company-news"
            params = {
                "symbol": ticker,
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
                "token": self.api_key
            }
            news = self._request(url, params)

            # Format news for consistency
            formatted_news = []
            for article in news[:limit]:
                formatted_news.append({
                    "title": article.get("headline", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                    "published_at": article.get("datetime", 0),
                    "summary": article.get("summary", "")
                })

            return formatted_news

        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {str(e)}")
            return []

    def get_analyst_recommendations(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch analyst recommendations from Finnhub

        Returns:
            Dict with buy/hold/sell/strongBuy/strongSell counts
        """
        if not self.api_key:
            logger.error("Finnhub API key not configured")
            return None

        try:
            url = f"{self.base_url}/stock/recommendation"
            params = {"symbol": ticker, "token": self.api_key}
            data = self._request(url, params)

            if not data or len(data) == 0:
                return None

            # Get most recent recommendation
            latest = data[0]

            return {
                "buy": latest.get("buy", 0),
                "hold": latest.get("hold", 0),
                "sell": latest.get("sell", 0),
                "strong_buy": latest.get("strongBuy", 0),
                "strong_sell": latest.get("strongSell", 0),
                "period": latest.get("period", "")
            }

        except Exception as e:
            logger.error(f"Error fetching analyst recommendations for {ticker}: {str(e)}")
            return None

    def get_earnings_calendar(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Fetch earnings calendar for a ticker

        Returns:
            List of upcoming/recent earnings dates
        """
        if not self.api_key:
            logger.error("Finnhub API key not configured")
            return []

        try:
            from datetime import datetime, timedelta

            # Get earnings from 30 days ago to 90 days in future
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now() + timedelta(days=90)

            url = f"{self.base_url}/calendar/earnings"
            params = {
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
                "symbol": ticker,
                "token": self.api_key
            }
            data = self._request(url, params)

            earnings = data.get("earningsCalendar", [])
            return earnings[:5]  # Limit to next 5 earnings

        except Exception as e:
            logger.error(f"Error fetching earnings calendar for {ticker}: {str(e)}")
            return []

    def get_earnings_history(self, ticker: str) -> List[Dict[str, Any]]:
        """Last four reported quarters: [{period, quarter, year, actual, estimate, surprisePercent}], newest first."""
        if not self.api_key:
            return []
        try:
            data = self._request(f"{self.base_url}/stock/earnings", {"symbol": ticker, "token": self.api_key})
            keep = ("period", "quarter", "year", "actual", "estimate", "surprise", "surprisePercent")
            return [{k: q.get(k) for k in keep} for q in (data or [])[:4]]
        except Exception as e:
            logger.error(f"Error fetching earnings history for {ticker}: {e}")
            return []

    def get_insider_transactions(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Fetch insider transactions (buys/sells by executives)

        Returns:
            List of recent insider transactions
        """
        if not self.api_key:
            logger.error("Finnhub API key not configured")
            return []

        try:
            from datetime import datetime, timedelta

            # Get insider trades from last 90 days
            start_date = datetime.now() - timedelta(days=90)

            url = f"{self.base_url}/stock/insider-transactions"
            params = {
                "symbol": ticker,
                "from": start_date.strftime("%Y-%m-%d"),
                "token": self.api_key
            }
            data = self._request(url, params)

            transactions = data.get("data", [])
            return transactions[:10]  # Limit to 10 most recent

        except Exception as e:
            logger.error(f"Error fetching insider transactions for {ticker}: {str(e)}")
            return []

    def get_basic_financials(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch basic financial metrics

        Returns:
            Dict with revenue, EPS, margins, etc.
        """
        if not self.api_key:
            logger.error("Finnhub API key not configured")
            return None

        try:
            url = f"{self.base_url}/stock/metric"
            params = {
                "symbol": ticker,
                "metric": "all",
                "token": self.api_key
            }
            data = self._request(url, params)

            if not data or "metric" not in data:
                return None

            metrics = data["metric"]

            return {
                "revenue_per_share": metrics.get("revenuePerShareTTM"),
                "eps": metrics.get("epsBasicExclExtraItemsTTM"),
                "profit_margin": metrics.get("netProfitMarginTTM"),
                "roe": metrics.get("roeTTM"),
                "roa": metrics.get("roaTTM"),
                "debt_to_equity": metrics.get("totalDebt/totalEquityQuarterly"),
                "current_ratio": metrics.get("currentRatioQuarterly"),
                "52_week_high": metrics.get("52WeekHigh"),
                "52_week_low": metrics.get("52WeekLow"),
                "beta": metrics.get("beta")
            }

        except Exception as e:
            logger.error(f"Error fetching financials for {ticker}: {str(e)}")
            return None

    def get_debut_price(self, ticker: str, ipo_date: str) -> Optional[float]:
        """
        Fetch the opening price on the IPO's first trading day.

        Args:
            ticker: Stock symbol
            ipo_date: Date string in YYYY-MM-DD format

        Returns:
            Opening price on IPO day, or None if unavailable
        """
        if not self.api_key:
            return None

        try:
            from datetime import datetime as dt, timedelta
            date = dt.strptime(ipo_date, "%Y-%m-%d")

            # Try the IPO date first, then the next day (pricing date vs. first trading day)
            for delta in (0, 1):
                candidate = date + timedelta(days=delta)
                from_ts = int(candidate.timestamp())
                to_ts = from_ts + 86400

                url = f"{self.base_url}/stock/candle"
                params = {
                    "symbol": ticker,
                    "resolution": "D",
                    "from": from_ts,
                    "to": to_ts,
                    "token": self.api_key,
                }
                data = self._request(url, params)

                if data.get("s") == "ok" and data.get("o"):
                    return data["o"][0]

            return None

        except Exception as e:
            logger.error(f"Error fetching debut price for {ticker} on {ipo_date}: {e}")
            return None

    def get_ipo_calendar(self, days_ahead: int = 90) -> List[Dict[str, Any]]:
        """
        Fetch IPO calendar (recent and upcoming)

        Args:
            days_ahead: Number of days to look ahead (default 90)

        Returns:
            List of recent and upcoming IPOs
        """
        if not self.api_key:
            logger.error("Finnhub API key not configured")
            return []

        try:
            from datetime import datetime, timedelta

            # Include past 30 days to show recent IPOs as well
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now() + timedelta(days=days_ahead)

            url = f"{self.base_url}/calendar/ipo"
            params = {
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
                "token": self.api_key
            }
            data = self._request(url, params)

            return data.get("ipoCalendar", [])

        except Exception as e:
            logger.error(f"Error fetching IPO calendar: {str(e)}")
            return []
