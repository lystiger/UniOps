from datetime import date

import pytest
from app.config import Settings
from app.integrations.easybooks.client import (
    PURCHASE_REPORT_PATH,
    SALES_DETAIL_PATH,
    SALES_LIST_PATH,
    EasyBooksClient,
    EasyBooksConfigurationError,
)


class RecordingTransport:
    def __init__(self):
        self.calls = []

    def request(self, method, path, *, params=None, json_body=None):
        self.calls.append((method, path, params, json_body))
        return []


def test_client_uses_only_known_read_calls():
    transport = RecordingTransport()
    settings = Settings(easybooks_company_id="fixture-company")
    client = EasyBooksClient(transport, settings)

    client.sales_documents(date(2026, 8, 1), date(2026, 8, 31))
    client.purchase_report(date(2026, 8, 1), date(2026, 8, 31))
    client.sales_lines("fixture-document-id")

    assert transport.calls[0][0:2] == ("GET", SALES_LIST_PATH)
    assert transport.calls[1][0:2] == ("POST", PURCHASE_REPORT_PATH)
    assert transport.calls[2][0:2] == ("GET", SALES_DETAIL_PATH)
    assert all(call[2].get("companyID") == "fixture-company" for call in transport.calls[:1])


def test_sales_detail_is_a_connector_constant_rather_than_configuration():
    client = EasyBooksClient(RecordingTransport(), Settings(easybooks_company_id="fixture"))

    client.sales_lines("fixture-document-id")

    method, path, params, json_body = client.transport.calls[0]
    assert (method, path) == ("GET", SALES_DETAIL_PATH)
    assert params == {"sAInvoiceID": "fixture-document-id"}
    assert json_body is None


def _live_transport(**overrides):
    from app.integrations.easybooks.client import HttpxReadOnlyTransport

    settings = Settings(
        easybooks_live_enabled=True,
        easybooks_company_id="fixture",
        easybooks_group="FIXTURE-GROUP",
        easybooks_bearer_token="operator-supplied",
        **overrides,
    )
    return HttpxReadOnlyTransport(settings)


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
def test_transport_refuses_every_method_that_is_not_a_known_read(method):
    transport = _live_transport()
    with pytest.raises(EasyBooksConfigurationError, match="not allowed"):
        transport.request(method, SALES_LIST_PATH)


def test_transport_refuses_post_to_the_sales_list():
    transport = _live_transport()
    with pytest.raises(EasyBooksConfigurationError, match="POST is not allowed"):
        transport.request("POST", SALES_LIST_PATH, json_body={"page": 1})


def test_live_transport_requires_live_mode_and_a_legitimate_credential():
    from app.integrations.easybooks.client import HttpxReadOnlyTransport

    with pytest.raises(EasyBooksConfigurationError, match="disabled"):
        HttpxReadOnlyTransport(Settings(easybooks_company_id="fixture"))
    with pytest.raises(EasyBooksConfigurationError, match="bearer token, session cookie"):
        HttpxReadOnlyTransport(
            Settings(easybooks_live_enabled=True, easybooks_company_id="fixture")
        )


def test_live_transport_requires_the_group_that_scopes_every_read():
    from app.integrations.easybooks.client import HttpxReadOnlyTransport

    with pytest.raises(EasyBooksConfigurationError, match="UNIOPS_EASYBOOKS_GROUP"):
        HttpxReadOnlyTransport(
            Settings(easybooks_live_enabled=True, easybooks_bearer_token="operator-supplied")
        )


def test_the_group_header_is_sent_on_every_live_read():
    transport = _live_transport()
    assert transport._client.headers["group"] == "FIXTURE-GROUP"


def test_blank_env_values_do_not_count_as_credentials_or_configuration():
    from app.integrations.easybooks.client import HttpxReadOnlyTransport

    settings = Settings(
        easybooks_live_enabled=True,
        easybooks_company_id="  ",
        easybooks_group="   ",
        easybooks_bearer_token="",
        easybooks_cookie="   ",
        easybooks_username="  ",
        easybooks_password="",
    )
    assert settings.easybooks_bearer_token is None
    assert settings.easybooks_cookie is None
    assert settings.easybooks_company_id is None
    assert settings.easybooks_group is None
    assert settings.easybooks_username is None
    assert settings.easybooks_password is None

    with pytest.raises(EasyBooksConfigurationError, match="bearer token, session cookie"):
        HttpxReadOnlyTransport(settings)


def test_an_unset_company_id_sends_the_empty_value_easybooks_accepts():
    # Observed live reads send an empty companyID and are scoped by the token.
    transport = RecordingTransport()
    EasyBooksClient(transport, Settings()).sales_documents(date(2026, 8, 1), date(2026, 8, 31))

    assert transport.calls[0][2]["companyID"] == ""


FROZEN_TODAY = date(2026, 9, 9)


def _report_client(**overrides):
    settings = Settings(**{"easybooks_company_id": "fixture-company", **overrides})
    return EasyBooksClient(RecordingTransport(), settings, today=lambda: FROZEN_TODAY)


def test_purchase_report_body_matches_the_observed_request_exactly():
    client = _report_client()

    body = client.purchase_report_body(date(2026, 5, 1), date(2026, 9, 8))

    assert body == {
        "toDate": "2026-09-08",
        "fromDate": "2026-05-01",
        "companyID": "fixture-company",
        "typeReport": "SO_CHI_TIET_MUA_HANG",
        "fileName": "SoNhatKiMuaHang.xlsx",
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
        "typeReportConfig": 11,
        "itemsPerPage": 30,
        "page": 1,
        "fromDateSecond": "2026-09-09",
        "toDateSecond": "2026-09-09",
    }


def test_purchase_report_carries_the_configured_company_id():
    body = _report_client(easybooks_company_id="another-company").purchase_report_body(
        date(2026, 5, 1), date(2026, 9, 8)
    )
    assert body["companyID"] == "another-company"


def test_purchase_report_uses_the_requested_window_not_the_secondary_dates():
    body = _report_client().purchase_report_body(date(2026, 1, 2), date(2026, 3, 4))

    assert (body["fromDate"], body["toDate"]) == ("2026-01-02", "2026-03-04")
    # Observed: the secondary pair tracked the current date, not the report range.
    assert body["fromDateSecond"] == body["toDateSecond"] == "2026-09-09"


def test_secondary_dates_come_from_an_injected_clock_not_the_wall_clock():
    body = EasyBooksClient(
        RecordingTransport(),
        Settings(easybooks_company_id="fixture-company"),
        today=lambda: date(2030, 1, 31),
    ).purchase_report_body(date(2026, 5, 1), date(2026, 9, 8))

    assert body["fromDateSecond"] == body["toDateSecond"] == "2030-01-31"


def test_business_today_uses_the_vietnam_calendar_date_not_utc():
    from datetime import UTC, datetime

    from app.integrations.easybooks.client import EASYBOOKS_TIMEZONE, business_today

    # 18:30 UTC is already the next calendar day in Vietnam (UTC+7).
    moment = datetime(2026, 9, 9, 18, 30, tzinfo=UTC)
    assert moment.astimezone(EASYBOOKS_TIMEZONE).date() == date(2026, 9, 10)
    assert business_today() == datetime.now(EASYBOOKS_TIMEZONE).date()


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("accountingObjects", []),
        ("listMaterialGoods", []),
        ("listRSProductionOrderID", []),
        ("employeeID", ""),
        ("mCodeFilter", ""),
        ("mNameFilter", ""),
        ("acCodeFilter", ""),
        ("acNameFilter", ""),
        ("acAddressFilter", ""),
        ("materialGoodsCategoryID", ""),
        ("dependent", False),
        ("isCheckAll", True),
        ("checkALL", True),
        ("isOnlyGetData", False),
        ("isCustomForm", True),
        ("typeReportConfig", 11),
        ("itemsPerPage", 30),
        ("page", 1),
    ],
)
def test_observed_purchase_report_constants_are_reproduced(field, expected):
    body = _report_client().purchase_report_body(date(2026, 5, 1), date(2026, 9, 8))
    assert body[field] == expected
    assert type(body[field]) is type(expected)


def test_purchase_report_posts_the_body_to_the_known_report_path():
    client = _report_client()

    client.purchase_report(date(2026, 5, 1), date(2026, 9, 8))

    method, path, params, json_body = client.transport.calls[0]
    assert (method, path) == ("POST", PURCHASE_REPORT_PATH)
    assert params is None
    assert json_body["typeReport"] == "SO_CHI_TIET_MUA_HANG"


# Shape of the body EasyBooks returns for a rejected credential: HTTP 500 whose
# message carries Spring Security's access-denied path. Values are synthetic.
AUTH_DENIED_BODY = {
    "code": 500,
    "status": "INTERNAL_SERVER_ERROR",
    "message": (
        "\nException: org.springframework.security.web.access.ExceptionTranslationFilter"
        ".handleAccessDeniedException(ExceptionTranslationFilter.java:194)"
    ),
}

# A genuine server fault: same status, no security markers.
SERVICE_FAULT_BODY = {
    "code": 500,
    "status": "INTERNAL_SERVER_ERROR",
    "message": (
        "Exception: vn.example.service.impl.SomeReportServiceImpl.getData"
        "(SomeReportServiceImpl.java:122)\nCause: java.lang.NullPointerException"
    ),
}


def _transport_answering(status_code, *, body=None):
    """A live transport whose HTTP calls are served by a stub, counting requests."""
    import httpx

    calls = []

    def handle(request):
        calls.append(request.url.path)
        return httpx.Response(status_code, json=body if body is not None else {})

    transport = _live_transport()
    transport._client = httpx.Client(
        transport=httpx.MockTransport(handle), base_url="https://easybooks.invalid"
    )
    return transport, calls


def test_an_expired_token_reports_what_to_do_instead_of_a_raw_status_error():
    from app.integrations.easybooks.client import EasyBooksAuthError

    transport, calls = _transport_answering(401)

    with pytest.raises(EasyBooksAuthError, match="most likely expired"):
        transport.request("GET", SALES_LIST_PATH)

    assert "UNIOPS_EASYBOOKS_BEARER_TOKEN" in str(
        pytest.raises(EasyBooksAuthError, transport.request, "GET", SALES_LIST_PATH).value
    )


def test_a_rejected_credential_is_not_retried():
    transport, calls = _transport_answering(401)

    with pytest.raises(EasyBooksConfigurationError):
        transport.request("GET", SALES_LIST_PATH)

    # One attempt only; retrying a stale token just repeats the rejection.
    assert len(calls) == 1


def test_a_forbidden_response_points_at_access_rather_than_the_token():
    from app.integrations.easybooks.client import EasyBooksAuthError

    transport, calls = _transport_answering(403)

    with pytest.raises(EasyBooksAuthError, match="not permitted") as caught:
        transport.request("GET", SALES_LIST_PATH)

    assert "expired" not in str(caught.value)
    assert len(calls) == 1


def test_an_auth_failure_never_echoes_the_credential():
    from app.integrations.easybooks.client import EasyBooksAuthError

    transport, _ = _transport_answering(401)

    with pytest.raises(EasyBooksAuthError) as caught:
        transport.request("GET", SALES_LIST_PATH)

    assert "operator-supplied" not in str(caught.value)
    assert "Bearer" not in str(caught.value)


def test_the_cli_reports_an_expired_token_as_a_refusal_not_a_traceback():
    from app.integrations.easybooks.client import EasyBooksAuthError

    # The CLI catches EasyBooksConfigurationError, so the auth error must be one.
    assert issubclass(EasyBooksAuthError, EasyBooksConfigurationError)


def test_server_errors_are_still_retried():
    import httpx

    transport, calls = _transport_answering(500, body=SERVICE_FAULT_BODY)
    transport._max_retries = 2

    with pytest.raises(httpx.HTTPStatusError):
        transport.request("GET", SALES_LIST_PATH)

    assert len(calls) == 3


def test_a_rejected_credential_returned_as_http_500_is_still_recognised():
    """EasyBooks answers a bad token with 500, so the status code is not enough."""
    from app.integrations.easybooks.client import EasyBooksAuthError

    transport, calls = _transport_answering(500, body=AUTH_DENIED_BODY)

    with pytest.raises(EasyBooksAuthError, match="most likely expired") as caught:
        transport.request("GET", SALES_LIST_PATH)

    assert "UNIOPS_EASYBOOKS_BEARER_TOKEN" in str(caught.value)
    assert len(calls) == 1


def test_a_genuine_server_fault_is_not_reported_as_an_expired_token():
    from app.integrations.easybooks.client import EasyBooksAuthError

    transport, _ = _transport_answering(500, body=SERVICE_FAULT_BODY)
    transport._max_retries = 0

    with pytest.raises(Exception) as caught:
        transport.request("GET", SALES_LIST_PATH)

    assert not isinstance(caught.value, EasyBooksAuthError)


def test_an_auth_failure_never_leaks_the_response_body():
    """The body carries the account email and a server stack trace."""
    from app.integrations.easybooks.client import EasyBooksAuthError

    transport, _ = _transport_answering(500, body=AUTH_DENIED_BODY)

    with pytest.raises(EasyBooksAuthError) as caught:
        transport.request("GET", SALES_LIST_PATH)

    message = str(caught.value)
    assert "springframework" not in message
    assert "Exception" not in message


def test_only_the_purchase_report_may_be_posted_to():
    """The sales dynamic report was removed, narrowing the write-capable surface."""
    from app.integrations.easybooks import client as client_module

    assert not hasattr(client_module, "SALES_REPORT_PATH")
    assert not hasattr(EasyBooksClient, "sales_report")

    transport = _live_transport()
    with pytest.raises(EasyBooksConfigurationError, match="POST is not allowed"):
        transport.request("POST", "/api/dynamic-report/ban-hang")
