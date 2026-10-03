import asyncio
import time

import httpx
import logging

from . import activity
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
    # Set when the analysis came from a bull/bear debate
    bull_case: Optional[str] = None
    bear_case: Optional[str] = None


CASE_PROMPT = (
    "\nArgue the strongest honest {side} case for this company in at most 150 words, using only the data "
    "above. Be specific (numbers, names, dates). Plain prose: no headings, lists or preamble."
)


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


# Sentinel-wide cap on concurrent LLM calls (syncs, filings, discover...), so a shared server keeps
# capacity for other users. One semaphore per event loop.
_slots: dict = {}


def _llm_slot() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    if loop not in _slots:
        from ..config import settings

        _slots.clear()  # only one loop runs at a time (tests start new ones)
        _slots[loop] = asyncio.Semaphore(max(1, settings.llm_max_concurrent))
    return _slots[loop]


def _saved_reasoning_effort() -> str:
    """The llm_reasoning_effort setting (read here so every caller picks it up)."""
    from ..database import SessionLocal
    from ..routers.settings import get_setting

    db = SessionLocal()
    try:
        return get_setting(db, "llm_reasoning_effort").strip()
    except Exception:
        return ""
    finally:
        db.close()


def _strings(value: Any, limit: int) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()][:limit]


def parse_analysis(text: str) -> Optional[Analysis]:
    """Parse the model's reply: JSON as requested, or the older SUMMARY:/SENTIMENT: text as a fallback."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0:
        data = None
        if end > start:
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        if data is None and "SUMMARY:" not in text:
            return None  # it tried to answer in JSON and got it wrong (or was cut off): let the caller retry
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

    def __init__(self, base_url: str, model: str, api_key: Optional[str] = None, reasoning_effort: Optional[str] = None):
        from ..config import settings as _settings

        # base_url includes the /v1 suffix, e.g. http://athena.lan:8090/v1
        self.base_url = base_url.rstrip("/")
        self.model = model
        key = _settings.llm_api_key if api_key is None else api_key
        self.headers = {"Authorization": f"Bearer {key}"} if key else {}
        # Set when generate() fails, so callers can report why
        self.last_error: Optional[str] = None
        # Sent as `reasoning_effort` when set (e.g. "low" / "medium"); not every server accepts it
        self.reasoning_effort = (reasoning_effort if reasoning_effort is not None else _saved_reasoning_effort()) or None

    async def generate(self, prompt: str, timeout: int = 60, json_mode: bool = False, purpose: str = "other") -> Optional[str]:
        """
        Generate text using the configured LLM.

        Args:
            prompt: The prompt to send to the LLM
            timeout: Request timeout in seconds

        Returns:
            Generated text or None if request fails (see last_error)

        Each call is recorded on the Activity page under `purpose`.
        """
        waited = time.perf_counter()
        async with _llm_slot():
            waited = time.perf_counter() - waited
            with activity.track("llm", purpose) as t:
                result = await self._generate(prompt, timeout, json_mode, t)
                if result is None:
                    t.fail(self.last_error or "no response")
                elif waited >= 1:
                    t.note(f"{self.model}, waited {waited:.0f}s for a free LLM slot")
                return result

    async def _generate(self, prompt: str, timeout: int, json_mode: bool, t) -> Optional[str]:
        self.last_error = None
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
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
                usage = data.get("usage") or {}
                t.prompt_tokens, t.completion_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
                t.note(self.model)
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
        peers: Optional[List[str]] = None,
        extra_context: Optional[str] = None,
        debate: bool = False,
    ) -> Tuple[Optional[Analysis], str]:
        """
        Analyze a company's data and news.

        `previous` is the last analysis ({"date", "sentiment", "summary", "price"}), so the model can
        say what changed. Returns (analysis, prompt); analysis is None if the LLM call failed
        (see last_error).
        """
        args = (company_name, ticker, status, stock_data, news_articles, analyst_ratings, insider_transactions)
        kwargs = dict(
            custom_instructions=custom_instructions, previous=previous, earnings_history=earnings_history,
            peers=peers, extra_context=extra_context,
        )
        cases = None
        if debate:
            # Bull and bear one after the other (not in parallel), so a shared LLM keeps a slot free
            data = self._build_analysis_prompt(*args, **kwargs, data_only=True)
            cases = []
            for side in ("bull", "bear"):
                text = await self.generate(data + CASE_PROMPT.format(side=side), timeout=300, purpose=f"{side} case")
                if text is None:
                    return None, data
                cases.append(text.strip())
        prompt = self._build_analysis_prompt(*args, **kwargs, debate_cases=cases)
        analysis = None
        for _ in range(2):  # models occasionally return malformed JSON; one retry usually fixes it
            response = await self.generate(prompt, timeout=300, json_mode=True, purpose="analysis")
            if response is None:
                return None, prompt
            analysis = parse_analysis(response)
            if analysis is not None:
                break
        if analysis is None:
            preview = re.sub(r"\s+", " ", response)[:160]
            self.last_error = f"the LLM's reply had no usable summary (it began: {preview!r})"
            return None, prompt
        if not previous:
            analysis.changes = None
        if cases:
            analysis.bull_case, analysis.bear_case = cases
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
        peers: Optional[List[str]] = None,
        extra_context: Optional[str] = None,
        debate_cases: Optional[List[str]] = None,
        data_only: bool = False,
    ) -> str:
        """Build the analysis prompt. data_only stops after the company data (for the debate cases)."""
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

        if peers:
            prompt += f"\nComparable companies (peers): {', '.join(peers)}\n"

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

        if extra_context:
            prompt += f"\n{extra_context.strip()}\n"
        if data_only:
            return prompt

        if previous:
            prompt += f"\nYour previous analysis ({previous['date']}"
            if previous.get("price") is not None:
                prompt += f", price then ${previous['price']:.2f}"
            prompt += f"):\nSentiment: {previous.get('sentiment') or 'none'}\n{previous['summary']}\n"

        if debate_cases:
            bull, bear = debate_cases
            prompt += (
                "\nTwo analysts argued opposite sides using the data above.\n"
                f"Bull case:\n{bull}\n\nBear case:\n{bear}\n\n"
                "Weigh both against the data. In the summary, say which case is stronger right now and why.\n"
            )

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
