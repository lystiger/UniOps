from datetime import date

import pytest
from app.config import Settings
from app.integrations.easybooks.client import (
    SALES_COUNT_PATH,
    SALES_DETAIL_PATH,
    SALES_LIST_PATH,
    EasyBooksClient,
)
from app.integrations.easybooks.sync import (
    _extract_count,
    _extract_rows,
    fetch_sales_documents,
)

WINDOW = (date(2026, 8, 1), date(2026, 8, 31))

# Parameter names EasyBooks would have to send if the sales list were paginated
# server-side. It is not: its UI pages the returned array client-side.
PAGING_PARAM_NAMES = {
    "page",
    "offset",
    "limit",
    "itemsPerPage",
    "pageSize",
    "pageIndex",
    "skip",
    "take",
    "start",
}


class StubTransport:
    """Serves canned responses per path and records every issued request."""

    def __init__(self, sales_list, count_response=None, count_error=None):
        self.sales_list = sales_list
        self.count_response = count_response
        self.count_error = count_error
        self.calls = []

    def request(self, method, path, *, params=None, json_body=None):
        self.calls.append((method, path, params, json_body))
        if path == SALES_COUNT_PATH:
            if self.count_error:
                raise self.count_error
            return self.count_response
        if path == SALES_LIST_PATH:
            return self.sales_list
        if path == SALES_DETAIL_PATH:
            return []
        raise AssertionError(f"unexpected path {path}")

    def calls_to(self, path):
        return [call for call in self.calls if call[1] == path]


def _document(index):
    return {"id": f"doc-{index}", "totalAmount": "1000.00"}


def _client(transport, **overrides):
    settings = Settings(easybooks_company_id="fixture-company", **overrides)
    return EasyBooksClient(transport, settings)


def test_sales_list_plain_array_is_read_whole_in_one_request():
    documents = [_document(index) for index in range(35)]
    transport = StubTransport(documents, count_response=35)

    retrieved, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert [item["id"] for item in retrieved] == [item["id"] for item in documents]
    assert warnings == []
    list_calls = transport.calls_to(SALES_LIST_PATH)
    assert len(list_calls) == 1
    assert list_calls[0][0] == "GET"
    assert list_calls[0][2] == {
        "companyID": "fixture-company",
        "fromDate": "2026-08-01",
        "toDate": "2026-08-31",
    }


def test_no_server_pagination_parameter_is_ever_sent():
    transport = StubTransport([_document(index) for index in range(35)], count_response=35)

    fetch_sales_documents(_client(transport), *WINDOW)

    for _method, _path, params, _json_body in transport.calls:
        assert PAGING_PARAM_NAMES.isdisjoint(params or {})


def test_bare_integer_count_matching_the_retrieved_documents_raises_no_warning():
    transport = StubTransport([_document(1), _document(2)], count_response=2)

    documents, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert len(documents) == 2
    assert warnings == []
    count_calls = transport.calls_to(SALES_COUNT_PATH)
    assert len(count_calls) == 1
    assert count_calls[0][0] == "GET"
    assert count_calls[0][2] == {
        "companyID": "fixture-company",
        "fromDate": "2026-08-01",
        "toDate": "2026-08-31",
    }


def test_count_mismatch_is_reported_without_blaming_pagination():
    transport = StubTransport([_document(1), _document(2)], count_response=35)

    documents, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert len(documents) == 2
    assert warnings == ["sales count reported 35 documents but 2 were retrieved"]
    assert not any("pagin" in warning.lower() for warning in warnings)
    # The mismatch is recorded, never silently accepted by dropping documents.
    assert [item["id"] for item in documents] == ["doc-1", "doc-2"]


def test_a_count_below_the_retrieved_total_is_also_a_mismatch():
    transport = StubTransport([_document(1), _document(2)], count_response=1)

    _, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert warnings == ["sales count reported 1 documents but 2 were retrieved"]


def test_an_empty_window_reports_zero_documents_and_no_warning():
    transport = StubTransport([], count_response=0)

    documents, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert documents == []
    assert warnings == []


def test_a_failing_count_read_is_advisory_and_never_aborts_ingestion():
    transport = StubTransport([_document(1)], count_error=RuntimeError("count endpoint 503"))

    documents, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert [item["id"] for item in documents] == ["doc-1"]
    assert any("count unavailable" in warning for warning in warnings)


def test_unrecognised_count_shape_is_reported_rather_than_guessed():
    transport = StubTransport([_document(1)], count_response={"unexpected": "shape"})

    _, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert warnings == ["sales count response was not a recognised number"]


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (35, 35),
        (0, 0),
        ("35", 35),
        (-1, None),
        (True, None),
        ("many", None),
        (None, None),
        ({"count": 7}, None),
        ([7], None),
    ],
)
def test_count_reader_takes_the_bare_integer_and_declines_everything_else(response, expected):
    assert _extract_count(response) == expected


def test_plain_array_and_unobserved_envelopes_both_yield_rows():
    assert _extract_rows([{"id": "doc-1"}]) == [{"id": "doc-1"}]
    assert _extract_rows([]) == []
    # The purchase report and sales detail envelopes were never directly observed.
    assert _extract_rows({"data": {"items": []}}) == []
    with pytest.raises(ValueError, match="did not contain a row list"):
        _extract_rows({"unexpected": "shape"})


def test_sales_detail_request_uses_the_observed_sainvoiceid_parameter():
    transport = StubTransport([])
    _client(transport).sales_lines("11111111-2222-3333-4444-555555555555")

    method, path, params, json_body = transport.calls[0]
    assert (method, path) == ("GET", SALES_DETAIL_PATH)
    assert params == {"sAInvoiceID": "11111111-2222-3333-4444-555555555555"}
    assert json_body is None


def test_sales_detail_request_does_not_use_a_bare_id_parameter_or_company_id():
    transport = StubTransport([])
    _client(transport).sales_lines("11111111-2222-3333-4444-555555555555")

    params = transport.calls[0][2]
    assert "id" not in params
    assert "companyID" not in params


def test_sales_detail_needs_no_operator_supplied_path():
    assert SALES_DETAIL_PATH == "/v2/api/sa-invoice-details/by-saInvoiceID"
    assert not hasattr(Settings(), "easybooks_sales_detail_path")


@pytest.mark.parametrize(
    "removed",
    [
        "easybooks_sales_page_size",
        "easybooks_sales_page_param",
        "easybooks_sales_page_size_param",
        "easybooks_sales_page_mode",
        "easybooks_sales_first_page",
        "easybooks_sales_max_pages",
    ],
)
def test_speculative_pagination_settings_are_gone(removed):
    assert removed not in Settings.model_fields
