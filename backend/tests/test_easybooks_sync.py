from copy import deepcopy
from datetime import date
from decimal import Decimal

from app.config import Settings
from app.integrations.easybooks.client import (
    PURCHASE_REPORT_PATH,
    SALES_COUNT_PATH,
    SALES_DETAIL_PATH,
    SALES_LIST_PATH,
    EasyBooksClient,
)
from app.integrations.easybooks.sync import FixtureBundle, fetch_live_bundle, sync_bundle
from app.models import (
    Customer,
    EasyBooksRawRecord,
    Product,
    PurchaseDocument,
    PurchaseLine,
    SalesDocument,
    SalesLine,
    SyncStatus,
)
from sqlalchemy import func, select


def _count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_fixture_sync_persists_normalized_and_raw_records(session, fixture_bundle):
    run = sync_bundle(session, fixture_bundle)

    assert run.status == SyncStatus.SUCCEEDED
    assert run.documents_seen == 2
    assert run.documents_created == 2
    assert run.reconciliation_warnings == 0
    assert _count(session, EasyBooksRawRecord) == 3
    assert _count(session, SalesDocument) == 1
    assert _count(session, SalesLine) == 1
    assert _count(session, PurchaseDocument) == 1
    assert _count(session, PurchaseLine) == 1
    assert _count(session, Customer) == 1
    assert _count(session, Product) == 2

    purchase_line = session.scalar(select(PurchaseLine))
    assert purchase_line.unit_price == Decimal("0.0000")
    assert purchase_line.purchase_amount == Decimal("2500000.00")


def test_repeated_sync_is_idempotent(session, fixture_bundle):
    first = sync_bundle(session, fixture_bundle)
    raw_count = _count(session, EasyBooksRawRecord)
    sales_line_id = session.scalar(select(SalesLine.id))
    purchase_line_id = session.scalar(select(PurchaseLine.id))

    second = sync_bundle(session, fixture_bundle)

    assert first.documents_created == 2
    assert second.documents_unchanged == 2
    assert second.documents_created == 0
    assert _count(session, EasyBooksRawRecord) == raw_count
    assert session.scalar(select(SalesLine.id)) == sales_line_id
    assert session.scalar(select(PurchaseLine.id)) == purchase_line_id


def test_changed_payload_creates_raw_version_and_updates_source(session, fixture_payload):
    first_bundle = FixtureBundle.from_dict(deepcopy(fixture_payload))
    sync_bundle(session, first_bundle)
    raw_count = _count(session, EasyBooksRawRecord)

    changed_payload = deepcopy(fixture_payload)
    changed_payload["sales_documents"][0]["accountingObjectName"] = "Updated Fixture Name"
    run = sync_bundle(session, FixtureBundle.from_dict(changed_payload))

    assert run.documents_updated == 1
    assert run.documents_unchanged == 1
    assert _count(session, EasyBooksRawRecord) == raw_count + 1
    assert session.scalar(select(Customer.name)) == "Updated Fixture Name"


def test_fixture_ingestion_is_retrievable_through_catalog_api(session, client, fixture_bundle):
    sync_bundle(session, fixture_bundle)

    customers = client.get("/api/customers")
    products = client.get("/api/products")

    assert customers.status_code == 200
    assert customers.json()[0]["easybooks_accounting_object_code"] == "KH-FIXTURE-01"
    assert products.status_code == 200
    assert {item["code"] for item in products.json()} == {
        "PAPER-FIX-01",
        "SERVICE-ELECTRICITY",
    }


def test_sync_run_metrics_are_exposed_read_only(session, client, fixture_bundle):
    run = sync_bundle(session, fixture_bundle)

    response = client.get("/api/sync-runs")

    assert response.status_code == 200
    latest = response.json()[0]
    assert latest["id"] == run.id
    assert latest["mode"] == "fixture"
    assert latest["status"] == "SUCCEEDED"
    assert latest["documents_seen"] == 2
    assert latest["documents_created"] == 2
    assert latest["reconciliation_warnings"] == 0


def test_header_only_sync_preserves_lines_and_repeats_idempotently(session, fixture_payload):
    full = FixtureBundle.from_dict(deepcopy(fixture_payload))
    sync_bundle(session, full)
    line_id = session.scalar(select(SalesLine.id))

    headers = FixtureBundle.from_dict(deepcopy(fixture_payload))
    headers.sales_lines = {}
    headers.sales_lines_available = False
    first = sync_bundle(session, headers, mode="live-headers")

    assert _count(session, SalesLine) == 1
    assert session.scalar(select(SalesLine.id)) == line_id

    second = sync_bundle(session, headers, mode="live-headers")
    assert first.documents_failed == 0
    assert second.documents_unchanged == 2
    assert second.documents_created == 0
    assert _count(session, SalesLine) == 1


def test_header_only_sync_does_not_raise_line_reconciliation_warnings(session, fixture_payload):
    headers = FixtureBundle.from_dict(deepcopy(fixture_payload))
    headers.sales_lines = {}
    headers.sales_lines_available = False

    run = sync_bundle(session, headers, mode="live-headers")

    assert run.documents_created == 2
    assert run.reconciliation_warnings == 0
    assert _count(session, SalesLine) == 0
    assert _count(session, Customer) == 1


def test_retrieval_warnings_are_counted_on_the_sync_run(session, fixture_bundle):
    fixture_bundle.warnings = ["sales count reported 9 documents but 2 were retrieved"]

    run = sync_bundle(session, fixture_bundle)

    assert run.reconciliation_warnings == 1
    assert run.documents_created == 2


class _LiveTransportStub:
    """Serves the three observed sales reads plus the purchase report."""

    def __init__(self, documents, details, count, purchase_rows=()):
        self.documents = documents
        self.details = details
        self.count = count
        self.purchase_rows = list(purchase_rows)
        self.calls = []

    def request(self, method, path, *, params=None, json_body=None):
        self.calls.append((method, path, params, json_body))
        if path == SALES_COUNT_PATH:
            return self.count
        if path == SALES_LIST_PATH:
            return self.documents
        if path == SALES_DETAIL_PATH:
            return self.details[params["sAInvoiceID"]]
        if path == PURCHASE_REPORT_PATH:
            return self.purchase_rows
        raise AssertionError(f"unexpected path {path}")


def _live_stub():
    documents = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "companyID": "fixture-company",
            "typeID": "SA_INVOICE",
            "date": "2026-08-10T00:00:00+07:00",
            "noBook": "BH-9001",
            "accountingObjectCode": "KH-FIXTURE-09",
            "accountingObjectName": "Sanitized Customer Nine",
            "totalAmount": "200000.00",
            "totalDiscountAmount": "0E-10",
            "totalVATAmount": "20000.00",
            "totalAllAmount": "220000.00",
            "total": "440000.00",
            "currencyID": "VND",
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "companyID": "fixture-company",
            "typeID": "SA_INVOICE",
            "date": "2026-08-11T00:00:00+07:00",
            "noBook": "BH-9002",
            "accountingObjectCode": "KH-FIXTURE-09",
            "accountingObjectName": "Sanitized Customer Nine",
            "totalAmount": "200000.00",
            "totalDiscountAmount": "0E-10",
            "totalVATAmount": "20000.00",
            "totalAllAmount": "220000.00",
            "total": None,
            "currencyID": "VND",
        },
    ]
    # Detail rows carry null id and null sAInvoiceID, as observed.
    details = {
        document["id"]: [
            {
                "id": None,
                "sAInvoiceID": None,
                "materialGoodsCode": f"PAPER-FIX-{index}",
                "materialGoodsName": "Sanitized converted paper",
                "unitName": "kg",
                "quantity": "100.0000",
                "unitPrice": "2000.0000",
                "amount": "200000.00",
                "discountAmount": "0E-10",
                "vATAmount": "20000.00",
            }
        ]
        for index, document in enumerate(documents)
    }
    return _LiveTransportStub(documents, details, count=2)


def _live_client(transport):
    return EasyBooksClient(transport, Settings(easybooks_company_id="fixture-company"))


def test_live_bundle_reads_list_count_and_one_detail_per_document(session):
    transport = _live_stub()
    bundle = fetch_live_bundle(_live_client(transport), date(2026, 8, 1), date(2026, 8, 31))

    detail_calls = [call for call in transport.calls if call[1] == SALES_DETAIL_PATH]
    assert [call[2] for call in detail_calls] == [
        {"sAInvoiceID": "11111111-1111-1111-1111-111111111111"},
        {"sAInvoiceID": "22222222-2222-2222-2222-222222222222"},
    ]
    assert len([call for call in transport.calls if call[1] == SALES_LIST_PATH]) == 1
    assert len([call for call in transport.calls if call[1] == SALES_COUNT_PATH]) == 1
    assert bundle.warnings == []

    run = sync_bundle(session, bundle, mode="live")

    assert run.status == SyncStatus.SUCCEEDED
    assert run.documents_created == 2
    assert run.reconciliation_warnings == 0
    assert _count(session, SalesLine) == 2


def test_live_lines_attach_to_the_document_used_to_request_them(session):
    bundle = fetch_live_bundle(_live_client(_live_stub()), date(2026, 8, 1), date(2026, 8, 31))
    sync_bundle(session, bundle, mode="live")

    for source_id in (
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    ):
        document = session.scalar(select(SalesDocument).where(SalesDocument.source_id == source_id))
        assert [line.source_line_id for line in document.lines] == [None]
        # The aggregate `total` never becomes a document amount.
        assert document.total_amount == Decimal("220000.00")


def test_repeated_live_sync_over_the_same_window_is_idempotent(session):
    window = (date(2026, 8, 1), date(2026, 8, 31))
    first = sync_bundle(
        session, fetch_live_bundle(_live_client(_live_stub()), *window), mode="live"
    )
    raw_count = _count(session, EasyBooksRawRecord)
    line_ids = sorted(session.scalars(select(SalesLine.id)))

    second = sync_bundle(
        session, fetch_live_bundle(_live_client(_live_stub()), *window), mode="live"
    )

    assert first.documents_created == 2
    assert second.documents_created == 0
    assert second.documents_unchanged == 2
    assert _count(session, EasyBooksRawRecord) == raw_count
    assert sorted(session.scalars(select(SalesLine.id))) == line_ids


def test_a_count_that_disagrees_with_the_list_is_recorded_as_a_warning(session):
    transport = _live_stub()
    transport.count = 35
    bundle = fetch_live_bundle(_live_client(transport), date(2026, 8, 1), date(2026, 8, 31))

    run = sync_bundle(session, bundle, mode="live")

    assert bundle.warnings == ["sales count reported 35 documents but 2 were retrieved"]
    assert run.reconciliation_warnings == 1
    # The discrepancy is reported, not silently accepted by discarding documents.
    assert run.documents_created == 2


def test_headers_only_live_read_skips_the_detail_route(session):
    transport = _live_stub()
    bundle = fetch_live_bundle(
        _live_client(transport), date(2026, 8, 1), date(2026, 8, 31), include_lines=False
    )

    assert not [call for call in transport.calls if call[1] == SALES_DETAIL_PATH]
    assert bundle.sales_lines_available is False

    run = sync_bundle(session, bundle, mode="live-headers")

    assert run.documents_created == 2
    assert _count(session, SalesLine) == 0


def _document_without_customer_code():
    """Mirrors the live list: it names the customer but carries no code."""
    return {
        "id": "33333333-3333-3333-3333-333333333333",
        "accountingObjectName": "Sanitized Customer Ten",
        "totalAmount": "100.00",
        "totalAllAmount": "100.00",
    }


def test_customer_is_catalogued_from_the_line_level_code(session):
    bundle = FixtureBundle(
        sales_documents=[_document_without_customer_code()],
        sales_lines={
            "33333333-3333-3333-3333-333333333333": [
                {"accountingObjectCode": "KH-LINE-01", "amount": "100.00"}
            ]
        },
    )

    run = sync_bundle(session, bundle)

    customer = session.scalar(select(Customer))
    assert run.reconciliation_warnings == 0
    assert customer is not None
    # Code comes from the line, name from the header.
    assert customer.easybooks_accounting_object_code == "KH-LINE-01"
    assert customer.name == "Sanitized Customer Ten"
    document = session.scalar(select(SalesDocument))
    assert document.accounting_object_code == "KH-LINE-01"


def test_a_header_code_is_not_overridden_by_the_lines(session):
    source = _document_without_customer_code() | {"accountingObjectCode": "KH-HEADER-01"}
    bundle = FixtureBundle(
        sales_documents=[source],
        sales_lines={
            "33333333-3333-3333-3333-333333333333": [
                {"accountingObjectCode": "KH-LINE-01", "amount": "100.00"}
            ]
        },
    )

    sync_bundle(session, bundle)

    assert session.scalar(select(SalesDocument)).accounting_object_code == "KH-HEADER-01"


def test_lines_disagreeing_on_customer_code_warn_and_catalogue_nobody(session):
    bundle = FixtureBundle(
        sales_documents=[_document_without_customer_code()],
        sales_lines={
            "33333333-3333-3333-3333-333333333333": [
                {"accountingObjectCode": "KH-LINE-01", "amount": "50.00"},
                {"accountingObjectCode": "KH-LINE-02", "amount": "50.00"},
            ]
        },
    )

    run = sync_bundle(session, bundle)

    assert run.reconciliation_warnings == 1
    assert _count(session, Customer) == 0
    assert session.scalar(select(SalesDocument)).accounting_object_code is None


def test_customer_linkage_from_lines_stays_idempotent(session):
    def build():
        return FixtureBundle(
            sales_documents=[_document_without_customer_code()],
            sales_lines={
                "33333333-3333-3333-3333-333333333333": [
                    {"accountingObjectCode": "KH-LINE-01", "amount": "100.00"}
                ]
            },
        )

    first = sync_bundle(session, build())
    second = sync_bundle(session, build())

    assert first.documents_created == 1
    assert second.documents_unchanged == 1
    assert _count(session, Customer) == 1


def test_headers_only_leaves_the_customer_code_unset_rather_than_guessing(session):
    bundle = FixtureBundle(
        sales_documents=[_document_without_customer_code()],
        sales_lines={},
        sales_lines_available=False,
    )

    run = sync_bundle(session, bundle, mode="live-headers")

    assert run.reconciliation_warnings == 0
    assert _count(session, Customer) == 0
    assert session.scalar(select(SalesDocument)).accounting_object_code is None
