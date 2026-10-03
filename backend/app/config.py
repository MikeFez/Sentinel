from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/sentinel.db"
    # Any OpenAI-compatible endpoint, including the /v1 suffix
    llm_base_url: str = "http://localhost:8080/v1"
    llm_model: str = "qwen3.8:27b"
    llm_api_key: str = ""
    # Most LLM calls Sentinel makes at once (across syncs, filings, discover); keep below the server's slots
    llm_max_concurrent: int = 1
    # Optional `reasoning_effort` for reasoning models (e.g. "low", "medium"); empty = server default
    llm_reasoning_effort: str = ""
    # SEC asks automated clients to identify themselves ("Name email@domain") and rejects requests
    # without a plausible contact; set SEC_USER_AGENT to your own
    sec_user_agent: str = "Sentinel/1.0 sentinel-selfhosted@example.org"
    news_article_count: int = 10
    finnhub_api_key: str = ""
    auto_refresh_enabled: bool = False
    auto_refresh_hours: float = 24.0
    staleness_hours: float = 24.0
    # How often to refresh quotes for public companies while the US market is open (0 = off)
    price_refresh_minutes: float = 5.0
    # Private / pre-IPO companies: refresh (news only) when older than this many days (0 = never)
    private_refresh_days: float = 7.0
    # Re-sync a public company when its price moves at least this much in a day (0 = off)
    move_sync_percent: float = 5.0
    # Re-sync after a company reports earnings
    earnings_sync: bool = True
    # Re-sync when analyst ratings shift or an insider makes a large trade (checked daily)
    signal_sync: bool = True
    # Keep full sync detail (news, prompts, insider data) for this many days (0 = forever)
    history_detail_days: float = 30.0
    # Summarize new SEC filings (8-K, 10-Q, 10-K) for public companies, checked daily
    filings_enabled: bool = True
    # "debate" (bull case, bear case, then a verdict: 3 LLM calls) or "single" (1 call)
    analysis_mode: str = "debate"
    # Guidance for the AI analysis. The output format is fixed by the app (see llm_service).
    ai_prompt_instructions: str = (
        "Write for an investor who already follows this company.\n"
        "- Weigh stock performance, analyst consensus, insider activity and the news.\n"
        "- If analysts show a strong consensus (mostly buy or mostly sell), say so.\n"
        "- Call out significant insider buying or selling; it can signal confidence or concern.\n"
        "- Be objective and balanced, and stick to facts from the data provided."
    )

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
