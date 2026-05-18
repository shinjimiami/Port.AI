from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "PortAI"
    DEBUG: bool = False
    # Comma-separated in env: "https://portai.vercel.app,http://localhost:3000"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str = "postgresql://portai:portai@localhost:5432/portai"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "insecure-dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 h

    # LLM
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    LLM_PROVIDER: str = "anthropic"  # "anthropic" | "groq" | "openai"
    LLM_MODEL: str = "claude-sonnet-4-6"

    # Market data
    ALPHA_VANTAGE_API_KEY: str = ""
    COINGECKO_API_KEY: str = ""
    NEWSAPI_KEY: str = ""

    # Business rules
    MAX_DAILY_GENERATIONS: int = 5
    MARKET_CACHE_TTL_SECONDS: int = 900  # 15 min


settings = Settings()
