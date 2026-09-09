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
