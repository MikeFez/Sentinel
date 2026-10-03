import httpx
import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any
import json
import re

logger = logging.getLogger(__name__)

SENTIMENTS = ("bullish", "bearish", "neutral", "mixed")

OUTPUT_FORMAT = """Respond with one JSON object and nothing else:
{
  "summary": "2-3 short paragraphs on recent developments and the company's current situation",
  "sentiment": "bullish" | "bearish" | "neutral" | "mixed",
  "key_points": ["up to 4 short, specific takeaways"],
  "risks": ["up to 3 short, specific risks"],
  "changes": "1-2 sentences on what is different since your previous analysis (news, price, sentiment), or null"
}"""


@dataclass
class Analysis:
    summary: str
    sentiment: str
    key_points: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    changes: Optional[str] = None


def clean_instructions(text: Optional[str]) -> Optional[str]:
    """Drop an output-format section from saved instructions: the app now sets the format itself.

    Instructions saved before the JSON format ended with "Format your response EXACTLY as follows:
    SUMMARY: ... SENTIMENT: ...", which would contradict it.
    """
    if not text or not text.strip():
        return None
    if "SENTIMENT:" in text:
        for marker in ("Format your response", "SUMMARY:"):
            cut = text.find(marker)
            if cut >= 0:
                text = text[:cut]
                break
    text = text.strip()
    return text or None


def _eps(value: float) -> str:
    """EPS with enough precision that close values don't look equal (e.g. -0.080 vs -0.077)."""
    return f"{value:.3f}" if abs(value) < 1 else f"{value:.2f}"


def _strings(value: Any, limit: int) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()][:limit]


def parse_analysis(text: str) -> Optional[Analysis]:
    """Parse the model's reply: JSON as requested, or the older SUMMARY:/SENTIMENT: text as a fallback."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("summary"), str) and data["summary"].strip():
            sentiment = str(data.get("sentiment", "")).strip().lower()
            changes = data.get("changes")
            return Analysis(
                summary=data["summary"].strip(),
                sentiment=sentiment if sentiment in SENTIMENTS else "neutral",
                key_points=_strings(data.get("key_points"), 4),
                risks=_strings(data.get("risks"), 3),
                changes=changes.strip() if isinstance(changes, str) and changes.strip() else None,
            )

    # Fallback: plain text, possibly in the old SUMMARY:/SENTIMENT: format
    summary = text
    sentiment = "neutral"
    if "SENTIMENT:" in text:
        tail = text[text.index("SENTIMENT:") + len("SENTIMENT:") :].lower()
        sentiment = next((w for w in SENTIMENTS if w in tail), "neutral")
        summary = text[: text.index("SENTIMENT:")]
    if "SUMMARY:" in summary:
        summary = summary[summary.index("SUMMARY:") + len("SUMMARY:") :]
    summary = summary.strip()
    if not summary or summary.startswith("{"):
        return None
    return Analysis(summary=summary, sentiment=sentiment)


class LLMService:
    """Service for interacting with an OpenAI-compatible chat completions API"""

    def __init__(self, base_url: str, model: str, api_key: Optional[str] = None):
        from ..config import settings as _settings

        # base_url includes the /v1 suffix, e.g. http://athena.lan:8090/v1
        self.base_url = base_url.rstrip("/")
        self.model = model
        key = _settings.llm_api_key if api_key is None else api_key
        self.headers = {"Authorization": f"Bearer {key}"} if key else {}
        # Set when generate() fails, so callers can report why
        self.last_error: Optional[str] = None

    async def generate(self, prompt: str, timeout: int = 60, json_mode: bool = False) -> Optional[str]:
        """
        Generate text using the configured LLM.

        Args:
            prompt: The prompt to send to the LLM
            timeout: Request timeout in seconds

        Returns:
            Generated text or None if request fails
        """
        self.last_error = None
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                url = f"{self.base_url}/chat/completions"
                response = await client.post(url, headers=self.headers, json=body)
                if json_mode and response.status_code in (400, 422):
                    # Some servers don't support response_format; the prompt asks for JSON anyway
                    body.pop("response_format")
                    response = await client.post(url, headers=self.headers, json=body)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"].get("content") or ""
                # Some servers return reasoning inline; drop it
                return re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()

        except httpx.TimeoutException:
            self.last_error = f"The LLM at {self.base_url} timed out after {timeout}s"
        except httpx.HTTPStatusError as e:
            self.last_error = f"The LLM returned HTTP {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            self.last_error = f"Could not reach the LLM at {self.base_url}: {e}"
        logger.error(f"LLM generation failed: {self.last_error}")
        return None

    async def analyze_company(
        self,
        company_name: str,
        ticker: Optional[str],
        status: str,
        stock_data: Optional[Dict[str, Any]],
        news_articles: List[Dict[str, Any]],
        analyst_ratings: Optional[Dict[str, Any]] = None,
        insider_transactions: Optional[List[Dict[str, Any]]] = None,
        custom_instructions: Optional[str] = None,
        previous: Optional[Dict[str, Any]] = None,
        earnings_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Optional[Analysis], str]:
        """
        Analyze a company's data and news.

        `previous` is the last analysis ({"date", "sentiment", "summary", "price"}), so the model can
        say what changed. Returns (analysis, prompt); analysis is None if the LLM call failed
        (see last_error).
        """
        prompt = self._build_analysis_prompt(
            company_name, ticker, status, stock_data, news_articles, analyst_ratings, insider_transactions,
            custom_instructions=custom_instructions, previous=previous, earnings_history=earnings_history,
        )
        response = await self.generate(prompt, timeout=180, json_mode=True)
        if response is None:
            return None, prompt
        analysis = parse_analysis(response)
        if analysis is None:
            self.last_error = "the LLM's reply had no usable summary"
        elif not previous:
            analysis.changes = None
        return analysis, prompt

    def _build_analysis_prompt(
        self,
        company_name: str,
        ticker: Optional[str],
        status: str,
        stock_data: Optional[Dict[str, Any]],
        news_articles: List[Dict[str, Any]],
        analyst_ratings: Optional[Dict[str, Any]] = None,
        insider_transactions: Optional[List[Dict[str, Any]]] = None,
        custom_instructions: Optional[str] = None,
        previous: Optional[Dict[str, Any]] = None,
        earnings_history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Build the prompt for company analysis"""
        prompt = f"""You are a financial analyst. Analyze the following information about {company_name}"""

        if ticker:
            prompt += f" ({ticker})"

        prompt += f""".\n\nCompany Status: {status.replace('_', ' ').title()}\n"""

        # Add stock data if available
        if stock_data:
            prompt += "\nStock Data:\n"
            if stock_data.get("stock_price"):
                prompt += f"- Current Price: ${stock_data['stock_price']:.2f}\n"
            if stock_data.get("price_change") is not None:
                prompt += f"- Price Change: {stock_data['price_change']:.2f}%\n"
            if stock_data.get("market_cap"):
                prompt += f"- Market Cap: {stock_data['market_cap']}\n"
            if stock_data.get("pe_ratio"):
                prompt += f"- P/E Ratio: {stock_data['pe_ratio']:.2f}\n"
        else:
            prompt += "\nStock Data: N/A (not publicly traded)\n"

        # Add analyst ratings if available
        if analyst_ratings:
            prompt += "\nAnalyst Ratings:\n"
            if analyst_ratings.get("buy"):
                prompt += f"- Buy: {analyst_ratings['buy']}\n"
            if analyst_ratings.get("hold"):
                prompt += f"- Hold: {analyst_ratings['hold']}\n"
            if analyst_ratings.get("sell"):
                prompt += f"- Sell: {analyst_ratings['sell']}\n"
            if analyst_ratings.get("strong_buy"):
                prompt += f"- Strong Buy: {analyst_ratings['strong_buy']}\n"
            if analyst_ratings.get("strong_sell"):
                prompt += f"- Strong Sell: {analyst_ratings['strong_sell']}\n"

        # Add insider transactions if available
        if insider_transactions and len(insider_transactions) > 0:
            prompt += f"\nRecent Insider Transactions ({len(insider_transactions)} transactions):\n"
            for i, txn in enumerate(insider_transactions[:5], 1):  # Limit to 5 most recent
                name = txn.get("name", "Unknown")
                shares = txn.get("share", 0)
                change = txn.get("change", 0)
                transaction_type = "Bought" if change > 0 else "Sold"
                prompt += f"{i}. {name} {transaction_type} {abs(change):,} shares\n"

        if earnings_history:
            prompt += "\nRecent Earnings (EPS actual vs estimate):\n"
            for q in earnings_history:
                if q.get("actual") is None:
                    continue
                label = f"Q{q.get('quarter')} {q.get('year')}" if q.get("quarter") else q.get("period", "")
                line = f"- {label}: {_eps(q['actual'])}"
                if q.get("estimate") is not None:
                    line += f" vs {_eps(q['estimate'])}"
                if q.get("surprisePercent") is not None:
                    line += f" ({'beat' if q['surprisePercent'] >= 0 else 'miss'} by {abs(q['surprisePercent']):.1f}%)"
                prompt += line + "\n"

        # Add news articles
        if news_articles:
            prompt += f"\nRecent News ({len(news_articles)} articles):\n"
            for i, article in enumerate(news_articles, 1):
                prompt += f"\n{i}. {article['title']}"
                if article.get("source"):
                    prompt += f" - {article['source']}"
                prompt += "\n"
        else:
            prompt += "\nRecent News: No recent news found\n"

        if previous:
            prompt += f"\nYour previous analysis ({previous['date']}"
            if previous.get("price") is not None:
                prompt += f", price then ${previous['price']:.2f}"
            prompt += f"):\nSentiment: {previous.get('sentiment') or 'none'}\n{previous['summary']}\n"

        from ..config import settings as _settings
        instructions = clean_instructions(custom_instructions) or _settings.ai_prompt_instructions
        prompt += f"\n{instructions}\n\n{OUTPUT_FORMAT}"
        if not previous:
            prompt += '\nThere is no previous analysis, so set "changes" to null.'
        return prompt

    async def list_models(self) -> List[str]:
        """
        List available models from the LLM endpoint.

        Returns:
            List of model names
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                response.raise_for_status()
                data = response.json()
                models = data.get("data", [])
                return [model.get("id") for model in models if model.get("id")]

        except Exception as e:
            logger.error(f"Failed to list LLM models: {str(e)}")
            return []

    async def check_health(self) -> bool:
        """
        Check if the LLM endpoint is available.

        Returns:
            True if the endpoint is responding, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/models", headers=self.headers)
                return response.status_code == 200
        except Exception:
            return False
