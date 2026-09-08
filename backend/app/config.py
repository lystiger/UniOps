from functools import lru_cache
from typing import Literal

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
    easybooks_sales_detail_path: str | None = None
    easybooks_request_timeout_seconds: float = 20.0
    easybooks_max_retries: int = 3
    easybooks_sync_overlap_days: int = 7

    # Sales list pagination. EasyBooks paging parameters were not among the observed
    # query dimensions, so UniOps never guesses their names. Leaving the page size
    # unset keeps the verified behaviour of one unpaginated sales list request.
    easybooks_sales_page_size: int | None = Field(default=None, gt=0)
    easybooks_sales_page_param: str | None = None
    easybooks_sales_page_size_param: str | None = None
    easybooks_sales_page_mode: Literal["offset", "page"] = "offset"
    easybooks_sales_first_page: int = 1
    easybooks_sales_max_pages: int = Field(default=200, gt=0)

    @field_validator(
        "easybooks_company_id",
        "easybooks_bearer_token",
        "easybooks_cookie",
        "easybooks_sales_detail_path",
        "easybooks_sales_page_size",
        "easybooks_sales_page_param",
        "easybooks_sales_page_size_param",
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
