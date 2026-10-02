from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"
    news_article_count: int = 10
    finnhub_api_key: str = ""
    auto_refresh_enabled: bool = False
    auto_refresh_hours: float = 24.0
    staleness_hours: float = 24.0
    ai_prompt_instructions: str = (
        "Based on the information above, provide:\n\n"
        "1. A concise summary (2-3 paragraphs) of recent developments and the company's current situation.\n"
        "   - Consider stock performance, analyst sentiment, insider activity, and news developments\n"
        "   - If analyst ratings show strong consensus (mostly buy or sell), mention it\n"
        "   - If insider transactions show significant buying or selling, note this as it can signal confidence or concern\n"
        "2. Overall sentiment analysis.\n\n"
        "Format your response EXACTLY as follows:\n\n"
        "SUMMARY:\n"
        "[Your 2-3 paragraph summary here]\n\n"
        "SENTIMENT: [Choose ONE: bullish, bearish, neutral, or mixed]\n\n"
        "Be objective and balanced in your analysis. Focus on facts from the data and news provided."
    )

    class Config:
        env_file = ".env"


settings = Settings()
