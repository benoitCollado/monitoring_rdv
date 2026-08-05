from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/odoo_link_monitor"

    # Empty means "no authentication" — fine for local dev, never for a deployed
    # instance: the dashboard exposes every generated link of every company.
    api_key: str = ""

    # The daily cron. Disable it in tests or when running a one-off CLI process.
    scheduler_enabled: bool = True

    check_timeout_seconds: float = 15.0
    check_concurrency: int = 8
    # How much of the response body we read to look for the error patterns.
    check_body_read_bytes: int = 200_000
    user_agent: str = "OdooLinkMonitor/1.0 (+link availability check)"

    # Comma-separated list, or "*".
    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
