from datetime import date

import pytest
from app.config import Settings
from app.integrations.easybooks.client import (
    PURCHASE_REPORT_PATH,
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

    assert transport.calls[0][0:2] == ("GET", SALES_LIST_PATH)
    assert transport.calls[1][0:2] == ("POST", PURCHASE_REPORT_PATH)
    assert all(call[2].get("companyID") == "fixture-company" for call in transport.calls[:1])


def test_sales_detail_path_must_be_operator_configured():
    client = EasyBooksClient(RecordingTransport(), Settings(easybooks_company_id="fixture"))
    with pytest.raises(EasyBooksConfigurationError, match="detail path is not known"):
        client.sales_lines("document-id")


def _live_transport(**overrides):
    from app.integrations.easybooks.client import HttpxReadOnlyTransport

    settings = Settings(
        easybooks_live_enabled=True,
        easybooks_company_id="fixture",
        easybooks_bearer_token="operator-supplied",
        **overrides,
    )
    return HttpxReadOnlyTransport(settings)


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
def test_transport_refuses_every_method_that_is_not_a_known_read(method):
    transport = _live_transport()
    with pytest.raises(EasyBooksConfigurationError, match="not allowed"):
        transport.request(method, SALES_LIST_PATH)


def test_transport_refuses_post_to_the_paginated_sales_list():
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


def test_paging_only_adds_query_parameters_to_the_known_sales_list_path():
    transport = RecordingTransport()
    client = EasyBooksClient(
        transport,
        Settings(
            easybooks_company_id="fixture-company",
            easybooks_sales_page_size=50,
            easybooks_sales_page_param="skip",
            easybooks_sales_page_size_param="take",
        ),
    )

    client.sales_documents(date(2026, 8, 1), date(2026, 8, 31), page_index=3)

    method, path, params, json_body = transport.calls[0]
    assert (method, path) == ("GET", SALES_LIST_PATH)
    assert json_body is None
    assert params["skip"] == 150
    assert params["take"] == 50


def test_blank_env_values_do_not_count_as_credentials_or_configuration():
    from app.integrations.easybooks.client import HttpxReadOnlyTransport

    settings = Settings(
        easybooks_live_enabled=True,
        easybooks_company_id="  ",
        easybooks_bearer_token="",
        easybooks_cookie="   ",
        easybooks_sales_page_size="",
        easybooks_sales_detail_path="",
    )
    assert settings.easybooks_bearer_token is None
    assert settings.easybooks_cookie is None
    assert settings.easybooks_company_id is None
    assert settings.easybooks_sales_page_size is None

    with pytest.raises(EasyBooksConfigurationError, match="bearer token or session cookie"):
        HttpxReadOnlyTransport(settings)
    with pytest.raises(EasyBooksConfigurationError, match="COMPANY_ID is required"):
        EasyBooksClient(RecordingTransport(), settings).sales_documents(
            date(2026, 8, 1), date(2026, 8, 31)
        )
