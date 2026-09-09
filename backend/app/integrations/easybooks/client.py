from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

SALES_LIST_PATH = "/v2/api/sa-invoice-objects-filter"
SALES_COUNT_PATH = "/v2/api/sa-invoice-count"
SALES_DETAIL_PATH = "/v2/api/sa-invoice-details/by-saInvoiceID"
SALES_REPORT_PATH = "/api/dynamic-report/ban-hang"
PURCHASE_REPORT_PATH = "/api/dynamic-report/mua-hang"

# EasyBooks is operated from Vietnam, so "today" must be that calendar date. Using
# UTC would roll over seven hours early and send the wrong business date.
EASYBOOKS_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")

# EasyBooks answers a rejected credential with HTTP 500, not 401, so the status
# code alone cannot identify one. Its body carries Spring Security's access-denied
# path, which a genuine business fault (a service NullPointerException, say) does
# not. Both an absent and a malformed token were observed producing these markers.
AUTH_FAILURE_MARKERS = (
    "exceptiontranslationfilter",
    "accessdeniedexception",
    "authenticationexception",
    "org.springframework.security",
)

PURCHASE_REPORT_TYPE = "SO_CHI_TIET_MUA_HANG"
PURCHASE_REPORT_FILE_NAME = "SoNhatKiMuaHang.xlsx"
PURCHASE_REPORT_TYPE_CONFIG = 11
PURCHASE_REPORT_ITEMS_PER_PAGE = 30
PURCHASE_REPORT_FIRST_PAGE = 1


def business_today() -> date:
    """The current EasyBooks business date, in the timezone the account runs in."""
    return datetime.now(EASYBOOKS_TIMEZONE).date()


class EasyBooksConfigurationError(RuntimeError):
    pass


class EasyBooksAuthError(EasyBooksConfigurationError):
    """The credential was rejected. A subclass so the CLI reports it as a refusal.

    Kept distinct from a transport failure because retrying a rejected credential
    only repeats the rejection.
    """


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
        # Without this header every filtered read returns an empty array instead of
        # an error, so an unset group would look like an empty accounting period.
        if not settings.easybooks_group:
            raise EasyBooksConfigurationError(
                "live mode requires UNIOPS_EASYBOOKS_GROUP; without it EasyBooks "
                "silently returns no rows"
            )
        headers["group"] = settings.easybooks_group
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
                # A rejected credential is terminal: retrying sends the same stale
                # token three more times and still fails, with a raw status error.
                if self._is_auth_failure(response):
                    raise EasyBooksAuthError(self._auth_failure_message(response.status_code))
                if response.status_code not in {408, 429} and response.status_code < 500:
                    response.raise_for_status()
                    return response.json()
                response.raise_for_status()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError):
                if attempt >= self._max_retries:
                    raise
                time.sleep(min(0.5 * (2**attempt), 4.0))
        raise RuntimeError("unreachable")

    @staticmethod
    def _is_auth_failure(response: httpx.Response) -> bool:
        """Decide whether a response is a rejected credential.

        401 and 403 are taken at face value. A 500 counts only when its body shows
        Spring Security's access-denied path, so an ordinary server fault is still
        treated as retryable rather than being reported as an expired token.
        """
        if response.status_code in {401, 403}:
            return True
        if response.status_code != 500:
            return False
        try:
            body = response.text.lower()
        except Exception:  # a body that cannot be read proves nothing either way
            return False
        return any(marker in body for marker in AUTH_FAILURE_MARKERS)

    @staticmethod
    def _auth_failure_message(status_code: int) -> str:
        """Explain a rejected credential without echoing it or the response body.

        The body is deliberately not quoted: EasyBooks includes the account email
        and a server stack trace in it.
        """
        if status_code == 403:
            return (
                "EasyBooks refused the request (HTTP 403). The credential is "
                "recognised but not permitted to read this data; check the account's "
                "access rather than replacing the token."
            )
        return (
            f"EasyBooks rejected the credential (HTTP {status_code}). The bearer "
            "token has most likely expired - they last 30 days. Copy a current one "
            "from an authenticated browser session into "
            "UNIOPS_EASYBOOKS_BEARER_TOKEN."
        )


class EasyBooksClient:
    def __init__(
        self,
        transport: Transport,
        settings: Settings,
        *,
        today: Callable[[], date] = business_today,
    ):
        self.transport = transport
        self.settings = settings
        # Injected so the report body stays deterministic under test instead of
        # depending on the wall clock.
        self._today = today

    def _company_id(self) -> str:
        """Return the configured companyID, or the empty value EasyBooks accepts.

        The observed requests send an empty companyID and are scoped by the bearer
        token's organisation instead; a populated value returns the same rows. It
        is kept as a request dimension but is no longer required.
        """
        return self.settings.easybooks_company_id or ""

    def sales_documents(self, from_date: date, to_date: date) -> Any:
        """Read the whole matching sales list in one request.

        EasyBooks returns every matching document in a single plain JSON array;
        its own UI paginates that array client-side and sends no paging query
        parameters. UniOps therefore issues exactly one request per window.
        """
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

    def _secondary_report_dates(self) -> dict[str, str]:
        """Build the report's secondary date pair.

        UNKNOWN SEMANTICS. The observed request carried fromDateSecond and
        toDateSecond both set to the current date while the report range itself
        was 2026-05-01..2026-09-08, so these are demonstrably *not* the report
        range. They are reproduced because the real UI sends them; no business
        logic depends on them and none should until their meaning is observed.
        """
        today = self._today().isoformat()
        return {"fromDateSecond": today, "toDateSecond": today}

    def purchase_report_body(
        self, from_date: date, to_date: date, *, page: int = PURCHASE_REPORT_FIRST_PAGE
    ) -> dict[str, Any]:
        """Reproduce the observed mua-hang request body.

        Only the date range, companyID, and page vary; every other value is the
        constant the EasyBooks web application sends. The previous partial body
        made the server raise a NullPointerException.
        """
        return {
            "toDate": to_date.isoformat(),
            "fromDate": from_date.isoformat(),
            "companyID": self._company_id(),
            "typeReport": PURCHASE_REPORT_TYPE,
            "fileName": PURCHASE_REPORT_FILE_NAME,
            "dependent": False,
            "accountingObjects": [],
            "listMaterialGoods": [],
            "listRSProductionOrderID": [],
            "employeeID": "",
            "isCheckAll": True,
            "checkALL": True,
            "mCodeFilter": "",
            "mNameFilter": "",
            "acCodeFilter": "",
            "acNameFilter": "",
            "acAddressFilter": "",
            "materialGoodsCategoryID": "",
            "isOnlyGetData": False,
            "isCustomForm": True,
            "typeReportConfig": PURCHASE_REPORT_TYPE_CONFIG,
            "itemsPerPage": PURCHASE_REPORT_ITEMS_PER_PAGE,
            "page": page,
            **self._secondary_report_dates(),
        }

    def purchase_report(
        self, from_date: date, to_date: date, *, page: int = PURCHASE_REPORT_FIRST_PAGE
    ) -> Any:
        return self.transport.request(
            "POST",
            PURCHASE_REPORT_PATH,
            json_body=self.purchase_report_body(from_date, to_date, page=page),
        )

    def sales_lines(self, document_id: str) -> Any:
        """Read the detail lines of one sales document.

        The observed contract keys on ``sAInvoiceID`` alone; no companyID is
        sent because the endpoint was never observed to require one.
        """
        return self.transport.request("GET", SALES_DETAIL_PATH, params={"sAInvoiceID": document_id})
