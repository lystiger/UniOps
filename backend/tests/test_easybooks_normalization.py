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
