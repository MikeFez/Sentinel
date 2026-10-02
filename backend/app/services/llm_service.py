import httpx
import logging
from typing import Optional, Tuple, List, Dict, Any
import json
import re

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with an OpenAI-compatible chat completions API"""

    def __init__(self, base_url: str, model: str, api_key: Optional[str] = None):
        from ..config import settings as _settings

        # base_url includes the /v1 suffix, e.g. http://athena.lan:8090/v1
        self.base_url = base_url.rstrip("/")
        self.model = model
        key = _settings.llm_api_key if api_key is None else api_key
        self.headers = {"Authorization": f"Bearer {key}"} if key else {}

    async def generate(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """
        Generate text using the configured LLM.

        Args:
            prompt: The prompt to send to the LLM
            timeout: Request timeout in seconds

        Returns:
            Generated text or None if request fails
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"].get("content") or ""
                # Some servers return reasoning inline; drop it
                return re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()

        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
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
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Analyze company data and news to generate summary and sentiment.

        Args:
            company_name: Name of the company
            ticker: Stock ticker (if public)
            status: Company status (public, pre_ipo, private, acquired)
            stock_data: Dictionary of stock metrics
            news_articles: List of news article dictionaries
            analyst_ratings: Analyst buy/sell/hold recommendations
            insider_transactions: Recent insider trading activity
            custom_instructions: Override the default analysis instructions

        Returns:
            Tuple of (summary, sentiment, prompt) or (None, None, None) if analysis fails
        """
        # Build the prompt
        prompt = self._build_analysis_prompt(
            company_name, ticker, status, stock_data, news_articles, analyst_ratings, insider_transactions,
            custom_instructions=custom_instructions,
        )

        # Get analysis from the LLM
        response = await self.generate(prompt)
        if not response:
            return None, None, None

        # Parse the response to extract summary and sentiment
        summary, sentiment = self._parse_analysis_response(response)
        return summary, sentiment, prompt

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

        # Add analysis instructions (custom or default)
        from ..config import settings as _settings
        instructions = custom_instructions or _settings.ai_prompt_instructions
        prompt += f"\n{instructions}\n"

        return prompt

    def _parse_analysis_response(self, response: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse the LLM response to extract summary and sentiment"""
        try:
            # Extract summary
            summary = None
            if "SUMMARY:" in response:
                summary_start = response.index("SUMMARY:") + len("SUMMARY:")
                sentiment_start = response.index("SENTIMENT:") if "SENTIMENT:" in response else len(response)
                summary = response[summary_start:sentiment_start].strip()

            # Extract sentiment
            sentiment = None
            if "SENTIMENT:" in response:
                sentiment_start = response.index("SENTIMENT:") + len("SENTIMENT:")
                sentiment_text = response[sentiment_start:].strip().lower()

                # Extract just the sentiment word
                for word in ["bullish", "bearish", "neutral", "mixed"]:
                    if word in sentiment_text:
                        sentiment = word
                        break

            # Default to neutral if parsing fails
            if not sentiment:
                sentiment = "neutral"

            return summary, sentiment

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return None, "neutral"

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
