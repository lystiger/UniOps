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
    with pytest.raises(EasyBooksConfigurationError, match="bearer token or session cookie"):
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
    )
    assert settings.easybooks_bearer_token is None
    assert settings.easybooks_cookie is None
    assert settings.easybooks_company_id is None
    assert settings.easybooks_group is None

    with pytest.raises(EasyBooksConfigurationError, match="bearer token or session cookie"):
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
