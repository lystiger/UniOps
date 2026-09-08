from datetime import date

import pytest
from app.config import Settings
from app.integrations.easybooks.client import (
    SALES_COUNT_PATH,
    SALES_LIST_PATH,
    EasyBooksClient,
    EasyBooksConfigurationError,
)
from app.integrations.easybooks.sync import (
    _extract_count,
    _extract_rows,
    fetch_sales_documents,
)

WINDOW = (date(2026, 8, 1), date(2026, 8, 31))


class StubTransport:
    """Returns queued responses per path and records every issued request."""

    def __init__(self, sales_pages, count_response=None, count_error=None):
        self.sales_pages = list(sales_pages)
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
            return self.sales_pages.pop(0) if self.sales_pages else []
        raise AssertionError(f"unexpected path {path}")


def _document(index):
    return {"id": f"doc-{index}", "totalAmount": "1000.00"}


def _client(transport, **overrides):
    settings = Settings(easybooks_company_id="fixture-company", **overrides)
    return EasyBooksClient(transport, settings)


def _paged(**overrides):
    return {
        "easybooks_sales_page_size": 2,
        "easybooks_sales_page_param": "skip",
        "easybooks_sales_page_size_param": "take",
        **overrides,
    }


def test_unpaginated_read_stays_a_single_request_when_paging_is_not_configured():
    transport = StubTransport([[_document(1), _document(2)]], count_response=2)
    documents, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert [item["id"] for item in documents] == ["doc-1", "doc-2"]
    assert warnings == []
    list_calls = [call for call in transport.calls if call[1] == SALES_LIST_PATH]
    assert len(list_calls) == 1
    assert set(list_calls[0][2]) == {"companyID", "fromDate", "toDate"}


def test_unpaginated_read_flags_a_count_that_exceeds_the_returned_page():
    transport = StubTransport([[_document(1), _document(2)]], count_response={"total": 57})
    documents, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert len(documents) == 2
    assert any("57 documents but 2 were retrieved" in warning for warning in warnings)
    assert any("paging is not configured" in warning for warning in warnings)


def test_offset_paging_walks_pages_and_stops_on_a_short_page():
    transport = StubTransport(
        [[_document(1), _document(2)], [_document(3), _document(4)], [_document(5)]],
        count_response=5,
    )
    documents, warnings = fetch_sales_documents(_client(transport, **_paged()), *WINDOW)

    assert [item["id"] for item in documents] == ["doc-1", "doc-2", "doc-3", "doc-4", "doc-5"]
    assert warnings == []
    list_calls = [call for call in transport.calls if call[1] == SALES_LIST_PATH]
    assert [call[2]["skip"] for call in list_calls] == [0, 2, 4]
    assert {call[2]["take"] for call in list_calls} == {2}
    assert {call[0] for call in transport.calls} == {"GET"}


def test_page_mode_sends_one_based_page_numbers():
    transport = StubTransport([[_document(1), _document(2)], [_document(3)]], count_response=3)
    client = _client(
        transport,
        **_paged(
            easybooks_sales_page_param="page",
            easybooks_sales_page_size_param="pageSize",
            easybooks_sales_page_mode="page",
        ),
    )
    fetch_sales_documents(client, *WINDOW)

    list_calls = [call for call in transport.calls if call[1] == SALES_LIST_PATH]
    assert [call[2]["page"] for call in list_calls] == [1, 2]


def test_paging_stops_once_the_reported_count_is_reached():
    transport = StubTransport(
        [[_document(1), _document(2)], [_document(3), _document(4)]], count_response=4
    )
    documents, warnings = fetch_sales_documents(_client(transport, **_paged()), *WINDOW)

    assert len(documents) == 4
    assert warnings == []
    assert len([call for call in transport.calls if call[1] == SALES_LIST_PATH]) == 2


def test_endpoint_that_ignores_paging_parameters_does_not_loop_forever():
    # No count is available, so only the repeated-page guard can stop the loop.
    repeated = [[_document(1), _document(2)] for _ in range(10)]
    transport = StubTransport(repeated, count_response=None)
    documents, warnings = fetch_sales_documents(_client(transport, **_paged()), *WINDOW)

    assert [item["id"] for item in documents] == ["doc-1", "doc-2"]
    assert len([call for call in transport.calls if call[1] == SALES_LIST_PATH]) == 2
    assert any("already-seen documents" in warning for warning in warnings)


def test_paging_stops_at_the_page_cap_and_reports_a_possibly_incomplete_window():
    pages = [[_document(index), _document(index + 100)] for index in range(10)]
    transport = StubTransport(pages, count_response=None)
    client = _client(transport, **_paged(easybooks_sales_max_pages=3))
    documents, warnings = fetch_sales_documents(client, *WINDOW)

    assert len(documents) == 6
    assert any("3-page cap" in warning for warning in warnings)


def test_paging_requires_operator_supplied_parameter_names():
    transport = StubTransport([[_document(1)]], count_response=1)
    client = _client(transport, easybooks_sales_page_size=2)

    assert client.paging_enabled() is True
    with pytest.raises(EasyBooksConfigurationError, match="will not guess"):
        fetch_sales_documents(client, *WINDOW)


def test_a_failing_count_read_is_advisory_and_never_aborts_ingestion():
    transport = StubTransport([[_document(1)]], count_error=RuntimeError("count endpoint 503"))
    documents, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert [item["id"] for item in documents] == ["doc-1"]
    assert any("count unavailable" in warning for warning in warnings)


def test_unrecognised_count_shape_is_reported_rather_than_guessed():
    transport = StubTransport([[_document(1)]], count_response={"unexpected": "shape"})
    _, warnings = fetch_sales_documents(_client(transport), *WINDOW)

    assert any("not a recognised number" in warning for warning in warnings)


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (7, 7),
        ("7", 7),
        ({"count": 7}, 7),
        ({"total": 7}, 7),
        ({"data": {"totalRows": 7}}, 7),
        ([{"totalResult": 7}], 7),
        (-1, None),
        (True, None),
        ("many", None),
        ({"unexpected": "shape"}, None),
    ],
)
def test_count_envelopes_resolve_or_decline(response, expected):
    assert _extract_count(response) == expected


def test_empty_nested_row_envelope_is_a_valid_empty_page():
    assert _extract_rows({"data": {"items": []}}) == []
    assert _extract_rows({"pageData": [{"id": "doc-1"}]}) == [{"id": "doc-1"}]
    with pytest.raises(ValueError, match="did not contain a row list"):
        _extract_rows({"unexpected": "shape"})
