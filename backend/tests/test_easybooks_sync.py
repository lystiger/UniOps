from copy import deepcopy
from decimal import Decimal

from app.integrations.easybooks.sync import FixtureBundle, sync_bundle
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
