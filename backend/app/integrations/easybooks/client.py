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
PURCHASE_REPORT_PATH = "/api/dynamic-report/mua-hang"
# Exchanges credentials for a bearer token. A POST that creates no business
# data, so it does not widen the read-only boundary.
AUTHENTICATE_PATH = "/api/authenticate"
# The web client calls this first: it reports whether the account needs an OTP
# and which organisations it may sign in against.
PRE_LOGIN_PATH = "/api/login-by-user"

# Observed success key is unverified across deployments, so accept the usual
# JHipster spellings and refuse rather than guess when none is present.
TOKEN_RESPONSE_KEYS = ("id_token", "idToken", "token", "access_token", "accessToken", "jwt")

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


def _orgs_from_trees(details: Any) -> list[str]:
    """List the organisations the account may sign in against.

    The web client shows these as a tree for a person to choose from.
    """
    trees = details.get("orgTrees") if isinstance(details, dict) else None
    found: list[str] = []
    if isinstance(trees, list):
        for node in trees:
            if not isinstance(node, dict):
                continue
            parent = node.get("parent")
            value = parent.get("id") if isinstance(parent, dict) else node.get("id")
            if isinstance(value, str) and value.strip():
                found.append(value.strip())
    return sorted(set(found))


def _token_from(response: Any) -> str:
    """Read the bearer token from an authenticate response body or header.

    The web client accepts either, so both are honoured.
    """
    payload = response.json() if getattr(response, "content", None) else None
    if isinstance(payload, dict):
        for key in TOKEN_RESPONSE_KEYS:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    header = getattr(response, "headers", {}).get("Authorization", "")
    if header.startswith("Bearer ") and header[7:].strip():
        return header[7:].strip()
    received = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
    raise EasyBooksAuthError(
        f"EasyBooks authenticate response carried no recognisable token; got {received}"
    )


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
        self._credentials: tuple[str, str] | None = None
        if settings.easybooks_username and settings.easybooks_password:
            self._credentials = (
                settings.easybooks_username,
                settings.easybooks_password.get_secret_value(),
            )
        if (
            "Authorization" not in headers
            and "Cookie" not in headers
            and self._credentials is None
        ):
            raise EasyBooksConfigurationError(
                "live mode requires legitimate EasyBooks bearer token, session cookie, "
                "or username and password"
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
        self._settings = settings
        if "Authorization" not in headers and self._credentials is not None:
            self._log_in()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        method = method.upper()
        if method == "POST" and path not in {
            PURCHASE_REPORT_PATH,
            AUTHENTICATE_PATH,
            PRE_LOGIN_PATH,
        }:
            raise EasyBooksConfigurationError(f"POST is not allowed for EasyBooks path {path}")
        if method not in {"GET", "POST"}:
            raise EasyBooksConfigurationError(f"{method} is not allowed for EasyBooks")

        renewed = False
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.request(method, path, params=params, json=json_body)
                if self._is_auth_failure(response):
                    # With credentials the token can be renewed once and the request
                    # retried. Without them, or if a renewed token is also rejected,
                    # the failure is terminal: resending it only repeats the answer.
                    if self._credentials is not None and not renewed:
                        renewed = True
                        self._log_in()
                        continue
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

    def _log_in(self) -> None:
        """Exchange credentials for a bearer token and adopt it.

        Neither the credentials nor the token are logged or included in any raised
        message.
        """
        if self._credentials is None:  # guarded by every caller
            raise EasyBooksConfigurationError("no EasyBooks credentials are configured")
        username, password = self._credentials
        logger.info("requesting a new EasyBooks token", extra={"source": "easybooks"})
        credentials = {"username": username, "password": password, "rememberMe": False}

        # Signing in without an organisation yields a token the data API refuses:
        # it carries no org/orgGetData/yearWork scoping. The org must be supplied.
        pre_login = self._client.post(PRE_LOGIN_PATH, json=credentials)
        if self._is_auth_failure(pre_login) or pre_login.status_code >= 400:
            raise EasyBooksAuthError(
                "EasyBooks rejected the configured username and password. Check "
                "UNIOPS_EASYBOOKS_USERNAME and UNIOPS_EASYBOOKS_PASSWORD."
            )
        details = pre_login.json() if pre_login.content else {}
        if isinstance(details, dict) and details.get("isOTP"):
            raise EasyBooksAuthError(
                "this EasyBooks account requires a one-time password, so it cannot "
                "sign in unattended. Configure UNIOPS_EASYBOOKS_BEARER_TOKEN instead, "
                "or use an account without OTP."
            )
        org = self._choose_org(details)

        response = self._client.post(
            AUTHENTICATE_PATH,
            json={**credentials, "org": org, "otp": False, "secretCode": ""},
        )
        if self._is_auth_failure(response) or response.status_code >= 400:
            # The credentials already passed pre-login, so the organisation is the
            # remaining variable. Say so rather than blaming the password.
            raise EasyBooksAuthError(
                "EasyBooks accepted the username and password but refused the sign-in "
                "for this organisation. Check UNIOPS_EASYBOOKS_ORG, or leave it unset "
                "to use the organisation the account reports."
            )
        self._client.headers["Authorization"] = f"Bearer {_token_from(response)}"

    def _choose_org(self, details: Any) -> str:
        """Pick the organisation, preferring an explicit setting but validating it.

        A configured value that the account does not offer is a misconfiguration -
        the company ID is easily pasted here by mistake - and signing in with it
        yields a rejection that looks like a bad password. Reject it by name instead.
        """
        offered = _orgs_from_trees(details)
        configured = self._settings.easybooks_org
        if configured:
            if offered and configured not in offered:
                raise EasyBooksAuthError(
                    f"UNIOPS_EASYBOOKS_ORG is not an organisation this account can use; "
                    f"it offers {len(offered)}. Leave the setting unset to use the "
                    f"reported organisation, and note it is not the company ID."
                )
            return configured
        if len(offered) == 1:
            return offered[0]
        raise EasyBooksAuthError(
            f"cannot choose an EasyBooks organisation automatically ({len(offered)} offered); "
            "set UNIOPS_EASYBOOKS_ORG to one the account can use"
        )

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
            "token has most likely expired. Copy a current one from an "
            "authenticated browser session into UNIOPS_EASYBOOKS_BEARER_TOKEN, or "
            "set UNIOPS_EASYBOOKS_USERNAME and UNIOPS_EASYBOOKS_PASSWORD so UniOps "
            "renews its own."
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
