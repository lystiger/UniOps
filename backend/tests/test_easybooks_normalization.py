from decimal import Decimal

import pytest
from app.integrations.easybooks.normalization import (
    normalize_purchase_document,
    normalize_purchase_lines,
    normalize_sales_document,
    normalize_sales_lines,
    reconcile_sales,
    source_decimal,
)


def test_decimal_handling_normalizes_exponent_zero():
    assert source_decimal("0E-10") == Decimal("0")
    assert source_decimal(12.5) == Decimal("12.5")
    assert source_decimal(None) == Decimal("0")


def test_sales_document_and_lines_use_requested_parent(fixture_payload):
    source = fixture_payload["sales_documents"][0]
    document = normalize_sales_document(source)
    lines = normalize_sales_lines(source["id"], fixture_payload["sales_lines"][source["id"]])

    assert document["source_id"] == "fixture-sale-001"
    assert document["subtotal"] == Decimal("1500000.00")
    assert lines[0]["source_line_id"] is None
    assert lines[0]["amount"] == Decimal("1500000.00")
    assert len(lines[0]["source_line_key"]) == 64


def test_fallback_sales_line_key_survives_amount_correction(fixture_payload):
    source_line = fixture_payload["sales_lines"]["fixture-sale-001"][0]
    before = normalize_sales_lines("fixture-sale-001", [source_line])[0]
    source_line["amount"] = "1499999.00"
    after = normalize_sales_lines("fixture-sale-001", [source_line])[0]
    assert before["source_line_key"] == after["source_line_key"]


def test_purchase_amount_is_authoritative_when_unit_price_is_zero(fixture_payload):
    row = fixture_payload["purchase_rows"][0]
    document = normalize_purchase_document(row["refID"], [row])
    line = normalize_purchase_lines(row["refID"], [row])[0]

    assert line["unit_price"] == Decimal("0")
    assert line["purchase_amount"] == Decimal("2500000.00")
    assert document["total_purchase_amount"] == Decimal("2500000.00")


def test_sales_reconciliation_allows_rounding_but_flags_material_difference(
    fixture_payload,
):
    source = fixture_payload["sales_documents"][0]
    document = normalize_sales_document(source)
    lines = normalize_sales_lines(source["id"], fixture_payload["sales_lines"][source["id"]])
    assert reconcile_sales(document, lines) == []

    lines[0]["amount"] += Decimal("0.50")
    assert reconcile_sales(document, lines) == []
    lines[0]["amount"] += Decimal("1.00")
    assert any("line subtotal" in warning for warning in reconcile_sales(document, lines))


def test_invalid_decimal_is_rejected():
    with pytest.raises(ValueError, match="invalid decimal"):
        source_decimal("not-money")


def test_aggregate_total_metadata_is_never_a_document_amount(fixture_payload):
    source = fixture_payload["sales_documents"][0]
    assert source["total"] == "99999999999.00"

    document = normalize_sales_document(source)

    assert document["subtotal"] == Decimal("1500000.00")
    assert document["discount_amount"] == Decimal("0")
    assert document["vat_amount"] == Decimal("150000.00")
    assert document["total_amount"] == Decimal("1650000.00")
    assert Decimal("99999999999.00") not in document.values()


def test_a_null_aggregate_total_on_later_rows_changes_nothing():
    # EasyBooks puts a result-set aggregate on the first row and null on the rest.
    first = {"id": "doc-1", "totalAmount": "100.00", "totalAllAmount": "110.00", "total": "330.00"}
    later = {"id": "doc-2", "totalAmount": "100.00", "totalAllAmount": "110.00", "total": None}

    assert normalize_sales_document(first)["total_amount"] == Decimal("110.00")
    assert normalize_sales_document(later)["total_amount"] == Decimal("110.00")


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

    assert document["subtotal"] == Decimal("0")
    assert document["discount_amount"] == Decimal("0")
    assert document["vat_amount"] == Decimal("0")
    assert document["total_amount"] == Decimal("0")
    assert str(document["subtotal"]) == "0"


def test_zero_document_vat_is_not_replaced_by_the_legacy_alias():
    document = normalize_sales_document({"id": "doc-1", "totalVATAmount": 0, "totalVAT": "150.00"})
    assert document["vat_amount"] == Decimal("0")

    fallback = normalize_sales_document({"id": "doc-1", "totalVAT": "150.00"})
    assert fallback["vat_amount"] == Decimal("150.00")


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

    assert [line["source_line_id"] for line in lines] == [None, None]
    assert len({line["source_line_key"] for line in lines}) == 2
    # The same line payload under a different parent gets a different identity.
    assert lines[0]["source_line_key"] != other[0]["source_line_key"]


def test_repeated_normalization_of_the_same_detail_is_stable():
    payload = [{"id": None, "sAInvoiceID": None, "materialGoodsCode": "P-1", "amount": "10.00"}]
    first = normalize_sales_lines("doc-1", payload)
    second = normalize_sales_lines("doc-1", payload)

    assert first[0]["source_line_key"] == second[0]["source_line_key"]
