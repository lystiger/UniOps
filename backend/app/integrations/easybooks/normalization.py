from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


class NormalizationError(ValueError):
    pass


def source_decimal(value: Any, *, default: str = "0") -> Decimal:
    """Convert source numbers through strings and collapse exponent-form zero."""
    if value is None or value == "":
        result = Decimal(default)
    elif isinstance(value, float):
        result = Decimal(str(value))
    else:
        try:
            result = Decimal(value)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise NormalizationError(f"invalid decimal value: {value!r}") from exc
    return Decimal("0") if result == 0 else result


def source_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(text[:10], "%d/%m/%Y").date()
        except ValueError as exc:
            raise NormalizationError(f"invalid date value: {value!r}") from exc


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def payload_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _text(value: Any) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _sales_vat_amount(source: dict[str, Any]) -> Any:
    """Prefer the observed per-document VAT field over the legacy alias.

    ``totalVATAmount`` is the observed document VAT. ``totalVAT`` is only read
    when the observed key is absent, so a genuine zero is never mistaken for a
    missing value.
    """
    if "totalVATAmount" in source:
        return source["totalVATAmount"]
    return source.get("totalVAT")


def normalize_sales_document(source: dict[str, Any]) -> dict[str, Any]:
    """Normalize one row of the observed sales list.

    Document-level money comes from ``totalAmount``, ``totalDiscountAmount``,
    ``totalVATAmount``, and ``totalAllAmount``. The list also carries a ``total``
    field, but that is result-set/report metadata: EasyBooks populates it with an
    aggregate on the first row and leaves it null on the rest, so it is never read
    as a document amount.
    """
    source_id = _text(source.get("id"))
    if not source_id:
        raise NormalizationError("sales document is missing stable id")
    normalized = {
        "source_system": "easybooks",
        "source_id": source_id,
        "source_type": _text(source.get("typeID") or source.get("typeName")),
        "source_document_number": _text(
            source.get("noBook") or source.get("noFBook") or source.get("noMBook")
        ),
        "company_id": _text(source.get("companyID")),
        "document_date": source_date(source.get("date")),
        "posted_date": source_date(source.get("postedDate")),
        "invoice_number": _text(source.get("invoiceNo")),
        "invoice_series": _text(source.get("invoiceSeries")),
        "accounting_object_code": _text(source.get("accountingObjectCode")),
        "accounting_object_name": _text(source.get("accountingObjectName")),
        "currency_id": _text(source.get("currencyID")),
        "subtotal": source_decimal(source.get("totalAmount")),
        "discount_amount": source_decimal(source.get("totalDiscountAmount")),
        "vat_amount": source_decimal(_sales_vat_amount(source)),
        "total_amount": source_decimal(source.get("totalAllAmount")),
        "recorded": source.get("recorded") if isinstance(source.get("recorded"), bool) else None,
    }
    normalized["normalized_hash"] = payload_hash(normalized)
    return normalized


def _fallback_sales_signature(source: dict[str, Any]) -> dict[str, Any]:
    # Monetary and quantity values are intentionally excluded so corrections update
    # an existing logical line. Duplicate occurrences disambiguate repeated products.
    return {
        "material_goods_id": source.get("materialGoodsID"),
        "material_goods_code": source.get("materialGoodsCode"),
        "material_goods_name": source.get("materialGoodsName"),
        "repository_id": source.get("repositoryID"),
        "repository_code": source.get("repositoryCode"),
        "debit_account": source.get("debitAccount"),
        "credit_account": source.get("creditAccount"),
        "unit": source.get("unitName"),
    }


def normalize_sales_lines(
    document_source_id: str, source_lines: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    occurrences: defaultdict[str, int] = defaultdict(int)
    result = []
    for source in source_lines:
        explicit_id = _text(source.get("id"))
        if explicit_id:
            line_key = payload_hash({"document": document_source_id, "line_id": explicit_id})
        else:
            signature = payload_hash(_fallback_sales_signature(source))
            occurrences[signature] += 1
            line_key = payload_hash(
                {
                    "document": document_source_id,
                    "signature": signature,
                    "occurrence": occurrences[signature],
                }
            )
        result.append(
            {
                "source_line_key": line_key,
                "source_line_id": explicit_id,
                "material_goods_id": _text(source.get("materialGoodsID")),
                "material_goods_code": _text(source.get("materialGoodsCode")),
                "material_goods_name": _text(source.get("materialGoodsName")),
                "repository_code": _text(source.get("repositoryCode")),
                "accounting_object_code": _text(source.get("accountingObjectCode")),
                "unit": _text(source.get("unitName")),
                "quantity": source_decimal(source.get("quantity")),
                "unit_price": source_decimal(source.get("unitPrice")),
                "amount": source_decimal(source.get("amount")),
                "discount_amount": source_decimal(source.get("discountAmount")),
                "vat_amount": source_decimal(source.get("vATAmount")),
            }
        )
    return result


def sales_customer_code(lines: list[dict[str, Any]]) -> tuple[str | None, list[str]]:
    """Derive a sales document's customer code from its detail lines.

    The observed sales list carries ``accountingObjectName`` but no
    ``accountingObjectCode``; the code appears only on detail lines, which in turn
    carry no name. Pairing the two is what links an EasyBooks document to a
    canonical customer.

    Every observed document agreed on one code across its lines. Disagreement is
    therefore unexpected rather than routine, so it yields no code and a warning
    instead of an arbitrary pick.
    """
    codes = {code for line in lines if (code := _text(line.get("accounting_object_code")))}
    if not codes:
        return None, []
    if len(codes) > 1:
        return None, [f"sales lines disagree on customer code: {sorted(codes)}"]
    return codes.pop(), []


def purchase_document_key(source: dict[str, Any]) -> str:
    ref_id = _text(source.get("refID"))
    if ref_id:
        return ref_id
    identity = {
        "number": source.get("soCTu") or source.get("soHoaDon"),
        "date": source.get("ngayCTu") or source.get("ngayHoaDon"),
        "vendor": source.get("accountingObjectCode") or source.get("maKH"),
        "type": source.get("typeID"),
    }
    if not any(identity.values()):
        raise NormalizationError("purchase row has no stable document identity")
    return f"fallback:{payload_hash(identity)}"


def group_purchase_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group purchase rows by document, ordering each group deterministically.

    The purchase report returns a document's rows in an unstable order: the same
    unchanged document was observed coming back with its rows permuted between
    consecutive requests. Left alone that made the payload hash differ every run,
    so unchanged documents were stored as new raw versions and reported as
    updated, and the raw table grew without bound.

    Sorting by canonical content loses nothing, since the source order carries no
    meaning, and it makes an unchanged document hash identically every time.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[purchase_document_key(row)].append(row)
    return {key: sorted(value, key=canonical_json) for key, value in grouped.items()}


def normalize_purchase_document(source_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise NormalizationError("purchase document has no rows")
    first = rows[0]
    normalized = {
        "source_system": "easybooks",
        "source_id": source_id,
        "source_type": _text(first.get("typeID")),
        "source_document_number": _text(first.get("soCTu")),
        "document_date": source_date(first.get("ngayCTu") or first.get("ngayHoaDon")),
        "posted_date": source_date(first.get("ngayHachToan")),
        "invoice_number": _text(first.get("soHoaDon")),
        "vendor_code": _text(first.get("accountingObjectCode") or first.get("maKH")),
        "vendor_name": _text(first.get("accountingObjectName") or first.get("tenKH")),
        "tax_code": _text(first.get("maSoThue")),
        "currency_rate": source_decimal(first.get("tyGia"), default="1"),
        # giaTriMua is authoritative, including service rows with zero unit price.
        "total_purchase_amount": sum(
            (source_decimal(row.get("giaTriMua")) for row in rows), Decimal("0")
        ),
    }
    normalized["normalized_hash"] = payload_hash(normalized)
    return normalized


def _fallback_purchase_signature(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "material_goods_code": source.get("mahang"),
        "material_goods_name": source.get("tenhang"),
        "unit": source.get("dvt"),
        "warehouse": source.get("maKho"),
        "debit": source.get("tkNo"),
        "credit": source.get("tkCo"),
        "description": source.get("dienGiai"),
    }


def normalize_purchase_lines(
    document_source_id: str, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    occurrences: defaultdict[str, int] = defaultdict(int)
    result = []
    for source in rows:
        signature = payload_hash(_fallback_purchase_signature(source))
        occurrences[signature] += 1
        line_key = payload_hash(
            {
                "document": document_source_id,
                "signature": signature,
                "occurrence": occurrences[signature],
            }
        )
        result.append(
            {
                "source_line_key": line_key,
                "material_goods_code": _text(source.get("mahang")),
                "material_goods_name": _text(source.get("tenhang")),
                "unit": _text(source.get("dvt")),
                "quantity": source_decimal(source.get("soLuongMua")),
                "unit_price": source_decimal(source.get("donGia")),
                "purchase_amount": source_decimal(source.get("giaTriMua")),
                "discount_amount": source_decimal(source.get("chietKhau")),
                "vat_amount": (
                    source_decimal(source.get("thueGTGT"))
                    if source.get("thueGTGT") not in (None, "")
                    else None
                ),
                "warehouse_code": _text(source.get("maKho")),
                "description": _text(source.get("dienGiai") or source.get("dienGiaiChung")),
            }
        )
    return result


def reconcile_sales(
    document: dict[str, Any], lines: list[dict[str, Any]], tolerance: Decimal = Decimal("1")
) -> list[str]:
    warnings = []
    line_amount = sum((line["amount"] for line in lines), Decimal("0"))
    line_vat = sum((line["vat_amount"] for line in lines), Decimal("0"))
    calculated_total = document["subtotal"] - document["discount_amount"] + document["vat_amount"]
    checks = (
        ("line subtotal", line_amount, document["subtotal"]),
        ("line VAT", line_vat, document["vat_amount"]),
        ("header total", calculated_total, document["total_amount"]),
    )
    for label, actual, expected in checks:
        if abs(actual - expected) > tolerance:
            warnings.append(f"{label} differs by {actual - expected}")
    return warnings
