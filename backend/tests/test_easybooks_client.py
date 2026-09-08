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
