"""
Central application configuration.

Every module that needs a config value (DB URL, API keys, model names,
Langfuse creds) should import `settings` from here rather than reading
os.environ directly. Keeps config in one place as the project grows
through the later steps (agent, ingestion, eval, observability).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_env: str = "development"
    log_level: str = "INFO"

    # --- OpenAI ---
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dim: int = 1536

    # --- Database ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/llmops_rag"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/llmops_rag"

    # --- Langfuse ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — import get_settings() rather than
    constructing Settings() directly, so env is only parsed once."""
    return Settings()


settings = get_settings()