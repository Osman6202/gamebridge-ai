"""GameBridge AI — backend configuration.

All settings come from environment variables so the same code runs locally,
in Docker, and on the deploy target. Secrets are NEVER hardcoded.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database: SQLite for dev + MVP deploy (no external infra dependency)
    database_url: str = "sqlite:///./gamebridge.db"

    # Security
    jwt_secret: str = "dev-secret-change-me"  # override via env in any real deploy
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # LLM provider (Week 2) — local/free default, no per-call cost
    # one of: ollama | hermes_free | claude
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    hermes_free_base_url: str = "http://localhost:8642"
    hermes_free_model: str = "tencent/hy3:free"
    claude_api_key: str = ""

    # Mock commerce API (used by test runner)
    mock_api_base: str = "http://localhost:8001"


settings = Settings()
