"""Data-quality invariants for the ingestion pipeline.

Raw idempotency, genuine-mutation detection, and purchase row-order stability are
covered in `test_easybooks_sync.py`, which owns the sync-outcome assertions. This
module covers what the layering itself must guarantee: lineage back to raw, an
append-only raw layer, referential integrity, and money that never becomes a
float on the way to a report.
"""

from datetime import date
from decimal import Decimal

from app.integrations.easybooks.normalization import payload_hash
from app.integrations.easybooks.reconciliation import check_integrity
from app.integrations.easybooks.sync import FixtureBundle, sync_bundle
from app.models import EasyBooksRawRecord, PurchaseDocument, SalesDocument, SalesLine
from app.services import analytics
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError


def _count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _sales_bundle(name: str = "Fixture Customer", address: str | None = None) -> FixtureBundle:
    document = {
        "id": "doc-1",
        "date": "2026-03-01",
        "accountingObjectName": name,
        "totalAmount": "100.00",
        "totalAllAmount": "100.00",
    }
    if address is not None:
        # A field UniOps reads from the source but never normalizes.
        document["accountingObjectAddress"] = address
    return FixtureBundle(
        sales_documents=[document],
        sales_lines={"doc-1": [{"accountingObjectCode": "KH-01", "amount": "100.00"}]},
    )


def test_a_normalized_document_names_the_raw_version_that_produced_it(session, fixture_bundle):
    sync_bundle(session, fixture_bundle)

    document = session.scalar(select(SalesDocument))
    header_raw = session.get(EasyBooksRawRecord, document.source_raw_record_id)
    lines_raw = session.get(EasyBooksRawRecord, document.source_lines_raw_record_id)

    assert header_raw.entity_type == "sales_document"
    assert header_raw.source_id == document.source_id
    assert header_raw.payload_hash == payload_hash(header_raw.payload)
    assert lines_raw.entity_type == "sales_lines"
    assert document.sync_run_id is not None


def test_a_purchase_document_names_its_raw_version(session):
    rows = [{"refID": "p-1", "ngayCTu": "2026-03-01", "mahang": "A", "giaTriMua": "10.00"}]
    sync_bundle(session, FixtureBundle(purchase_rows=rows))

    document = session.scalar(select(PurchaseDocument))
    raw = session.get(EasyBooksRawRecord, document.source_raw_record_id)

    assert raw.entity_type == "purchase_document"
    assert raw.source_id == document.source_id


def test_lineage_follows_a_genuine_change_and_the_old_version_survives(session):
    sync_bundle(session, _sales_bundle())
    original_raw_id = session.scalar(select(SalesDocument)).source_raw_record_id
    original_payload = session.get(EasyBooksRawRecord, original_raw_id).payload

    run = sync_bundle(session, _sales_bundle(name="Renamed Customer"))

    document = session.scalar(select(SalesDocument))
    assert run.documents_updated == 1
    assert document.source_raw_record_id != original_raw_id
    assert document.accounting_object_name == "Renamed Customer"
    # The superseded version is still there, byte for byte.
    superseded = session.get(EasyBooksRawRecord, original_raw_id)
    assert superseded is not None
    assert superseded.payload == original_payload
    assert _count(session, EasyBooksRawRecord) == 3


def test_lineage_moves_even_when_the_normalized_content_does_not_change(session):
    """A source can change in a field UniOps does not normalize.

    The normalized row is then correctly reported unchanged, but it is now
    explained by a newer raw version, and the pointer has to say so.
    """
    sync_bundle(session, _sales_bundle(address="Old address"))
    first_raw_id = session.scalar(select(SalesDocument)).source_raw_record_id

    run = sync_bundle(session, _sales_bundle(address="New address"))

    document = session.scalar(select(SalesDocument))
    assert run.documents_unchanged == 1
    assert run.documents_updated == 0
    assert document.source_raw_record_id != first_raw_id
    assert session.get(EasyBooksRawRecord, first_raw_id) is not None


def test_the_raw_layer_is_append_only(session):
    sync_bundle(session, _sales_bundle())
    before = {
        record.id: (record.payload_hash, payload_hash(record.payload))
        for record in session.scalars(select(EasyBooksRawRecord))
    }

    sync_bundle(session, _sales_bundle(name="Renamed Customer"))
    sync_bundle(session, _sales_bundle(name="Renamed Again"))

    after = {
        record.id: (record.payload_hash, payload_hash(record.payload))
        for record in session.scalars(select(EasyBooksRawRecord))
    }
    # Every earlier version is still present and still holds the same bytes.
    for raw_id, fingerprint in before.items():
        assert after[raw_id] == fingerprint
    assert len(after) > len(before)


def test_a_clean_sync_leaves_no_integrity_warning(session, fixture_bundle):
    run = sync_bundle(session, fixture_bundle)
    report = check_integrity(session)

    assert report.warnings == []
    assert report.orphan_sales_lines == 0
    assert report.orphan_purchase_lines == 0
    assert report.sales_documents_without_lineage == 0
    assert run.reconciliation_warnings == 0


def test_an_orphan_line_is_either_refused_or_reported(session, fixture_bundle):
    sync_bundle(session, fixture_bundle)
    session.add(
        SalesLine(
            sales_document_id="no-such-document",
            source_line_key="orphan",
            quantity=Decimal("1"),
            unit_price=Decimal("1"),
            amount=Decimal("1"),
            discount_amount=Decimal("0"),
            vat_amount=Decimal("0"),
        )
    )
    try:
        session.commit()
    except IntegrityError:
        # PostgreSQL enforces the foreign key, which is the stronger guarantee.
        session.rollback()
        return
    # SQLite does not enforce it unless asked, so the check has to find it.
    assert check_integrity(session).orphan_sales_lines == 1


def test_a_document_without_lineage_is_reported_on_the_next_run(session, fixture_bundle):
    session.add(
        SalesDocument(
            source_system="easybooks",
            source_id="legacy-document",
            normalized_hash="unknown",
        )
    )
    session.commit()

    run = sync_bundle(session, fixture_bundle)

    assert check_integrity(session).sales_documents_without_lineage == 1
    assert run.reconciliation_warnings == 1
    assert run.documents_failed == 0


def test_every_normalized_line_resolves_to_its_document(session, fixture_bundle):
    sync_bundle(session, fixture_bundle)

    unresolved = session.scalar(
        select(func.count())
        .select_from(SalesLine)
        .where(
            ~select(SalesDocument.id)
            .where(SalesDocument.id == SalesLine.sales_document_id)
            .exists()
        )
    )
    assert unresolved == 0


def _floats(value, path="result"):
    """Every float found in a nested result, with where it was found."""
    if isinstance(value, float):
        return [path]
    if isinstance(value, dict):
        return [f for key, item in value.items() for f in _floats(item, f"{path}.{key}")]
    if isinstance(value, list | tuple):
        return [f for index, item in enumerate(value) for f in _floats(item, f"{path}[{index}]")]
    if hasattr(value, "__dataclass_fields__"):
        return [
            f
            for name in value.__dataclass_fields__
            for f in _floats(getattr(value, name), f"{path}.{name}")
        ]
    return []


def test_no_float_reaches_a_financial_aggregate(session):
    sync_bundle(
        session,
        FixtureBundle(
            sales_documents=[
                {
                    "id": "s-1",
                    "date": "2026-04-01",
                    "accountingObjectCode": "KH-01",
                    "accountingObjectName": "Customer",
                    "totalAmount": "0.10",
                    "totalAllAmount": "0.10",
                },
                {
                    "id": "s-2",
                    "date": "2026-04-02",
                    "accountingObjectCode": "KH-01",
                    "accountingObjectName": "Customer",
                    "totalAmount": "0.20",
                    "totalAllAmount": "0.20",
                },
            ],
            sales_lines={},
            sales_lines_available=False,
        ),
    )

    result = analytics.overview(session, date(2026, 1, 1), date(2026, 12, 31))

    assert _floats(result) == []
    # The classic float failure: 0.1 + 0.2 is 0.30000000000000004 in binary
    # floating point. Summing in Decimal keeps it exact.
    assert result.sales.total == Decimal("0.30")
    assert result.sales_minus_purchases == Decimal("0.30")


def test_an_inverted_window_is_refused_before_the_database_is_touched(session):
    calls = []
    original = analytics._within
    analytics._within = lambda *args, **kwargs: calls.append(args) or original(*args, **kwargs)
    try:
        try:
            analytics.overview(session, date(2026, 12, 1), date(2026, 1, 1))
        except analytics.InvalidDateWindow:
            pass
        else:
            raise AssertionError("an inverted window was accepted")
    finally:
        analytics._within = original
    assert calls == []


def _report_total_row() -> dict:
    """The observed grand-total footer: money, a label, and no identity."""
    return {
        "soCTu": "Tổng cộng",
        "maKH": None,
        "ngayCTu": None,
        "ngayHoaDon": None,
        "ngayHachToan": None,
        "refID": None,
        "typeID": None,
        "mahang": None,
        "soLuongMua": 141413.91,
        "giaTriMua": 3434358898.0,
        "chietKhau": 0.0,
    }


def _real_purchase_row(ref: str, amount: str) -> dict:
    return {
        "refID": ref,
        "typeID": "PURCHASE",
        "maKH": "NCC-01",
        "tenKH": "Vendor One",
        "ngayCTu": "2026-05-02",
        "soCTu": f"MH-{ref}",
        "mahang": "NL.TS86",
        "tenhang": "Paper reel",
        "dvt": "kg",
        "soLuongMua": "1.0000",
        "donGia": amount,
        "giaTriMua": amount,
    }


def test_the_report_total_footer_is_not_ingested_as_a_purchase(session):
    rows = [_real_purchase_row("p-1", "10.00"), _real_purchase_row("p-2", "20.00")]
    run = sync_bundle(session, FixtureBundle(purchase_rows=[*rows, _report_total_row()]))

    assert _count(session, PurchaseDocument) == 2
    # Dropped, but said out loud: a change in the report's shape must be visible.
    assert run.reconciliation_warnings == 1
    assert run.documents_seen == 2


def test_the_total_footer_does_not_double_the_purchase_total(session):
    rows = [_real_purchase_row("p-1", "10.00"), _real_purchase_row("p-2", "20.00")]
    sync_bundle(session, FixtureBundle(purchase_rows=[*rows, _report_total_row()]))

    summary = analytics.purchase_summary(session)

    assert summary.total == Decimal("30.00")
    assert summary.document_count == 2
    assert summary.undated_document_count == 0


def test_a_purchase_row_identified_only_by_its_date_is_still_ingested(session):
    """The footer filter keys on having no identity at all, not on a missing refID."""
    row = _real_purchase_row("p-1", "10.00") | {"refID": None, "maKH": None, "typeID": None}
    run = sync_bundle(session, FixtureBundle(purchase_rows=[row]))

    assert run.documents_created == 1
    assert _count(session, PurchaseDocument) == 1
    assert run.reconciliation_warnings == 0
