from dataclasses import replace
from decimal import Decimal

import pytest
from app.integrations.easybooks.contracts import SalesLineRecord
from app.integrations.easybooks.normalization import (
    group_purchase_rows,
    normalize_purchase_document,
    normalize_purchase_lines,
    normalize_sales_document,
    normalize_sales_lines,
    payload_hash,
    sales_customer_code,
    source_decimal,
)
from app.integrations.easybooks.reconciliation import reconcile_sales
from app.models import PurchaseDocument, PurchaseLine


def _sales_line(**overrides) -> SalesLineRecord:
    """A normalized sales line with only the field under test set."""
    defaults = dict(
        source_line_key="key",
        source_line_id=None,
        material_goods_id=None,
        material_goods_code=None,
        material_goods_name=None,
        repository_code=None,
        accounting_object_code=None,
        unit=None,
        quantity=Decimal("0"),
        unit_price=Decimal("0"),
        amount=Decimal("0"),
        discount_amount=Decimal("0"),
        vat_amount=Decimal("0"),
    )
    return SalesLineRecord(**(defaults | overrides))


def test_decimal_handling_normalizes_exponent_zero():
    assert source_decimal("0E-10") == Decimal("0")
    assert source_decimal(12.5) == Decimal("12.5")
    assert source_decimal(None) == Decimal("0")


def test_sales_document_and_lines_use_requested_parent(fixture_payload):
    source = fixture_payload["sales_documents"][0]
    document = normalize_sales_document(source)
    lines = normalize_sales_lines(source["id"], fixture_payload["sales_lines"][source["id"]])

    assert document.source_id == "fixture-sale-001"
    assert document.subtotal == Decimal("1500000.00")
    assert lines[0].source_line_id is None
    assert lines[0].amount == Decimal("1500000.00")
    assert len(lines[0].source_line_key) == 64


def test_fallback_sales_line_key_survives_amount_correction(fixture_payload):
    source_line = fixture_payload["sales_lines"]["fixture-sale-001"][0]
    before = normalize_sales_lines("fixture-sale-001", [source_line])[0]
    source_line["amount"] = "1499999.00"
    after = normalize_sales_lines("fixture-sale-001", [source_line])[0]
    assert before.source_line_key == after.source_line_key


def test_purchase_amount_is_authoritative_when_unit_price_is_zero(fixture_payload):
    row = fixture_payload["purchase_rows"][0]
    document = normalize_purchase_document(row["refID"], [row])
    line = normalize_purchase_lines(row["refID"], [row])[0]

    assert line.unit_price == Decimal("0")
    assert line.purchase_amount == Decimal("2500000.00")
    assert document.total_purchase_amount == Decimal("2500000.00")


def test_sales_reconciliation_allows_rounding_but_flags_material_difference(
    fixture_payload,
):
    source = fixture_payload["sales_documents"][0]
    document = normalize_sales_document(source)
    lines = normalize_sales_lines(source["id"], fixture_payload["sales_lines"][source["id"]])
    assert reconcile_sales(document, lines) == []

    # Records are frozen, so a corrected amount is a new record, not a mutation.
    lines[0] = replace(lines[0], amount=lines[0].amount + Decimal("0.50"))
    assert reconcile_sales(document, lines) == []
    lines[0] = replace(lines[0], amount=lines[0].amount + Decimal("1.00"))
    assert any("line subtotal" in warning for warning in reconcile_sales(document, lines))


def test_invalid_decimal_is_rejected():
    with pytest.raises(ValueError, match="invalid decimal"):
        source_decimal("not-money")


def test_aggregate_total_metadata_is_never_a_document_amount(fixture_payload):
    source = fixture_payload["sales_documents"][0]
    assert source["total"] == "99999999999.00"

    document = normalize_sales_document(source)

    assert document.subtotal == Decimal("1500000.00")
    assert document.discount_amount == Decimal("0")
    assert document.vat_amount == Decimal("150000.00")
    assert document.total_amount == Decimal("1650000.00")
    assert Decimal("99999999999.00") not in document.as_hash_payload().values()


def test_a_null_aggregate_total_on_later_rows_changes_nothing():
    # EasyBooks puts a result-set aggregate on the first row and null on the rest.
    first = {"id": "doc-1", "totalAmount": "100.00", "totalAllAmount": "110.00", "total": "330.00"}
    later = {"id": "doc-2", "totalAmount": "100.00", "totalAllAmount": "110.00", "total": None}

    assert normalize_sales_document(first).total_amount == Decimal("110.00")
    assert normalize_sales_document(later).total_amount == Decimal("110.00")


def test_exponent_form_zero_survives_every_document_money_field():
    document = normalize_sales_document(
        {
            "id": "doc-1",
            "totalAmount": "0E-10",
            "totalDiscountAmount": "0E-10",
            "totalVATAmount": "0E-10",
            "totalAllAmount": "0E-10",
        }
    )

    assert document.subtotal == Decimal("0")
    assert document.discount_amount == Decimal("0")
    assert document.vat_amount == Decimal("0")
    assert document.total_amount == Decimal("0")
    assert str(document.subtotal) == "0"


def test_zero_document_vat_is_not_replaced_by_the_legacy_alias():
    document = normalize_sales_document({"id": "doc-1", "totalVATAmount": 0, "totalVAT": "150.00"})
    assert document.vat_amount == Decimal("0")

    fallback = normalize_sales_document({"id": "doc-1", "totalVAT": "150.00"})
    assert fallback.vat_amount == Decimal("150.00")


def test_detail_lines_with_null_identity_bind_to_the_requested_document():
    lines = normalize_sales_lines(
        "doc-1",
        [
            {"id": None, "sAInvoiceID": None, "materialGoodsCode": "P-1", "amount": "10.00"},
            {"id": None, "sAInvoiceID": None, "materialGoodsCode": "P-2", "amount": "20.00"},
        ],
    )
    other = normalize_sales_lines(
        "doc-2",
        [{"id": None, "sAInvoiceID": None, "materialGoodsCode": "P-1", "amount": "10.00"}],
    )

    assert [line.source_line_id for line in lines] == [None, None]
    assert len({line.source_line_key for line in lines}) == 2
    # The same line payload under a different parent gets a different identity.
    assert lines[0].source_line_key != other[0].source_line_key


def test_repeated_normalization_of_the_same_detail_is_stable():
    payload = [{"id": None, "sAInvoiceID": None, "materialGoodsCode": "P-1", "amount": "10.00"}]
    first = normalize_sales_lines("doc-1", payload)
    second = normalize_sales_lines("doc-1", payload)

    assert first[0].source_line_key == second[0].source_line_key


def test_customer_code_comes_from_lines_when_they_agree():
    lines = [
        _sales_line(accounting_object_code="KH-01", amount=Decimal("10")),
        _sales_line(accounting_object_code="KH-01", amount=Decimal("20")),
    ]
    assert sales_customer_code(lines) == ("KH-01", [])


def test_no_customer_code_on_any_line_is_not_an_error():
    assert sales_customer_code([_sales_line()]) == (None, [])
    assert sales_customer_code([]) == (None, [])


def test_lines_that_disagree_on_customer_code_warn_instead_of_picking_one():
    code, warnings = sales_customer_code(
        [
            _sales_line(accounting_object_code="KH-01"),
            _sales_line(accounting_object_code="KH-02"),
        ]
    )

    assert code is None
    assert warnings == ["sales lines disagree on customer code: ['KH-01', 'KH-02']"]


def test_purchase_rows_group_in_a_stable_order_whatever_the_source_order():
    """The report permutes a document's rows between identical requests."""
    rows = [
        {"refID": "doc-1", "mahang": "B", "giaTriMua": "20.00"},
        {"refID": "doc-1", "mahang": "A", "giaTriMua": "10.00"},
        {"refID": "doc-1", "mahang": "C", "giaTriMua": "30.00"},
    ]
    forward = group_purchase_rows(rows)
    reversed_order = group_purchase_rows(list(reversed(rows)))
    shuffled = group_purchase_rows([rows[2], rows[0], rows[1]])

    assert forward == reversed_order == shuffled
    assert [row["mahang"] for row in forward["doc-1"]] == ["A", "B", "C"]


def test_a_permuted_document_hashes_identically():
    rows = [
        {"refID": "doc-1", "mahang": "B", "giaTriMua": "20.00"},
        {"refID": "doc-1", "mahang": "A", "giaTriMua": "10.00"},
    ]
    first = payload_hash(group_purchase_rows(rows)["doc-1"])
    second = payload_hash(group_purchase_rows(list(reversed(rows)))["doc-1"])

    assert first == second


def test_grouping_still_separates_distinct_documents():
    grouped = group_purchase_rows(
        [
            {"refID": "doc-2", "mahang": "A"},
            {"refID": "doc-1", "mahang": "A"},
            {"refID": "doc-1", "mahang": "B"},
        ]
    )

    assert sorted(grouped) == ["doc-1", "doc-2"]
    assert len(grouped["doc-1"]) == 2
    assert len(grouped["doc-2"]) == 1


def test_purchase_vat_is_read_as_an_amount_not_a_percentage():
    """`thueGTGT` carries VAT in dong. An 8% invoice line proves the scale."""
    lines = normalize_purchase_lines(
        "doc-1",
        [{"mahang": "NL.TS86", "giaTriMua": "157533480", "thueGTGT": "12602678"}],
    )
    assert lines[0].vat_amount == Decimal("12602678")
    ratio = lines[0].vat_amount / lines[0].purchase_amount
    assert ratio.quantize(Decimal("0.0001")) == Decimal("0.0800")


def test_a_real_purchase_vat_amount_fits_the_column(session):
    """The column was NUMERIC(8,4).

    SQLite stores anything regardless of the declared precision, so this only
    ever failed once a real invoice reached PostgreSQL, which refused it with
    "numeric field overflow". Run the suite against Postgres to exercise it.
    """
    document = PurchaseDocument(source_id="purchase-1", normalized_hash="hash")
    session.add(document)
    session.flush()
    session.add(
        PurchaseLine(
            purchase_document_id=document.id,
            source_line_key="line-1",
            vat_amount=Decimal("12602678.00"),
        )
    )
    session.commit()

    stored = session.query(PurchaseLine).one()
    assert stored.vat_amount == Decimal("12602678.00")
