from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="UNIOPS_", extra="ignore", case_sensitive=False
    )

    database_url: str = "sqlite:///./uniops.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    log_level: str = "INFO"

    easybooks_live_enabled: bool = False
    easybooks_base_url: str = "https://app133.easybooks.vn"
    easybooks_company_id: str | None = None
    easybooks_bearer_token: SecretStr | None = None
    easybooks_cookie: SecretStr | None = None
    easybooks_request_timeout_seconds: float = 20.0
    easybooks_max_retries: int = 3
    easybooks_sync_overlap_days: int = 7

    @field_validator(
        "easybooks_company_id",
        "easybooks_bearer_token",
        "easybooks_cookie",
        mode="before",
    )
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        """Treat a blank .env entry as absent.

        Without this an empty UNIOPS_EASYBOOKS_BEARER_TOKEN would satisfy the
        credential check and send an empty Authorization header.
        """
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
