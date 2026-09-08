from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Protocol

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

SALES_LIST_PATH = "/v2/api/sa-invoice-objects-filter"
SALES_COUNT_PATH = "/v2/api/sa-invoice-count"
SALES_REPORT_PATH = "/api/dynamic-report/ban-hang"
PURCHASE_REPORT_PATH = "/api/dynamic-report/mua-hang"


class EasyBooksConfigurationError(RuntimeError):
    pass


class Transport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any: ...


class HttpxReadOnlyTransport:
    """Authenticated transport constrained to GET and known report POST requests."""

    def __init__(self, settings: Settings):
        if not settings.easybooks_live_enabled:
            raise EasyBooksConfigurationError("live EasyBooks reads are disabled")
        headers = {"Accept": "application/json"}
        if settings.easybooks_bearer_token:
            token = settings.easybooks_bearer_token.get_secret_value()
            headers["Authorization"] = f"Bearer {token}"
        if settings.easybooks_cookie:
            headers["Cookie"] = settings.easybooks_cookie.get_secret_value()
        if "Authorization" not in headers and "Cookie" not in headers:
            raise EasyBooksConfigurationError(
                "live mode requires legitimate EasyBooks bearer token or session cookie"
            )
        self._client = httpx.Client(
            base_url=settings.easybooks_base_url,
            headers=headers,
            timeout=settings.easybooks_request_timeout_seconds,
        )
        self._max_retries = settings.easybooks_max_retries

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        method = method.upper()
        if method == "POST" and path not in {SALES_REPORT_PATH, PURCHASE_REPORT_PATH}:
            raise EasyBooksConfigurationError(f"POST is not allowed for EasyBooks path {path}")
        if method not in {"GET", "POST"}:
            raise EasyBooksConfigurationError(f"{method} is not allowed for EasyBooks")

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.request(method, path, params=params, json=json_body)
                if response.status_code not in {408, 429} and response.status_code < 500:
                    response.raise_for_status()
                    return response.json()
                response.raise_for_status()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError):
                if attempt >= self._max_retries:
                    raise
                time.sleep(min(0.5 * (2**attempt), 4.0))
        raise RuntimeError("unreachable")


class EasyBooksClient:
    def __init__(self, transport: Transport, settings: Settings):
        self.transport = transport
        self.settings = settings

    def _company_id(self) -> str:
        if not self.settings.easybooks_company_id:
            raise EasyBooksConfigurationError("UNIOPS_EASYBOOKS_COMPANY_ID is required")
        return self.settings.easybooks_company_id

    def sales_documents(self, from_date: date, to_date: date) -> Any:
        return self.transport.request(
            "GET",
            SALES_LIST_PATH,
            params={
                "companyID": self._company_id(),
                "fromDate": from_date.isoformat(),
                "toDate": to_date.isoformat(),
            },
        )

    def sales_count(self, from_date: date, to_date: date) -> Any:
        return self.transport.request(
            "GET",
            SALES_COUNT_PATH,
            params={
                "companyID": self._company_id(),
                "fromDate": from_date.isoformat(),
                "toDate": to_date.isoformat(),
            },
        )

    def sales_report(self, from_date: date, to_date: date) -> Any:
        return self.transport.request(
            "POST",
            SALES_REPORT_PATH,
            json_body={
                "companyID": self._company_id(),
                "fromDate": from_date.isoformat(),
                "toDate": to_date.isoformat(),
                "typeReport": "SO_CHI_TIET_BAN_HANG",
            },
        )

    def purchase_report(self, from_date: date, to_date: date) -> Any:
        return self.transport.request(
            "POST",
            PURCHASE_REPORT_PATH,
            json_body={
                "companyID": self._company_id(),
                "fromDate": from_date.isoformat(),
                "toDate": to_date.isoformat(),
            },
        )

    def sales_lines(self, document_id: str) -> Any:
        path = self.settings.easybooks_sales_detail_path
        if not path:
            raise EasyBooksConfigurationError(
                "sales detail path is not known; configure an observed read-only path"
            )
        if "{document_id}" in path:
            path = path.replace("{document_id}", document_id)
            params = {"companyID": self._company_id()}
        else:
            params = {"companyID": self._company_id(), "id": document_id}
        return self.transport.request("GET", path, params=params)
