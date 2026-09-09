"""The mart layer: derived read models over the accounting tables."""

from datetime import date
from decimal import Decimal

import pytest
from app.integrations.easybooks.sync import FixtureBundle, sync_bundle
from app.services import analytics


def _sale(source_id: str, day: str | None, total: str, vat: str, customer: str) -> dict:
    return {
        "id": source_id,
        "date": day,
        "accountingObjectCode": customer,
        "accountingObjectName": f"Customer {customer}",
        "totalAmount": total,
        "totalVATAmount": vat,
        "totalAllAmount": total,
    }


def _purchase(ref: str, day: str, amount: str, vat: str, vendor: str) -> dict:
    return {
        "refID": ref,
        "ngayCTu": day,
        "maKH": vendor,
        "tenKH": f"Vendor {vendor}",
        "mahang": "NL.TS86",
        "tenhang": "Paper reel",
        "dvt": "kg",
        "soLuongMua": "1.0000",
        "donGia": amount,
        "giaTriMua": amount,
        "thueGTGT": vat,
    }


@pytest.fixture
def ledger(session):
    """Two months of sales and purchases, plus one undated sales document."""
    sync_bundle(
        session,
        FixtureBundle(
            sales_documents=[
                _sale("s-1", "2026-01-15", "1000000.00", "80000.00", "KH-01"),
                _sale("s-2", "2026-01-20", "2000000.00", "160000.00", "KH-02"),
                _sale("s-3", "2026-02-10", "500000.00", "40000.00", "KH-01"),
                _sale("s-4", None, "999999.00", "0.00", "KH-09"),
            ],
            sales_lines={},
            sales_lines_available=False,
            purchase_rows=[
                _purchase("p-1", "2026-01-05", "700000.00", "56000.00", "NCC-01"),
                _purchase("p-2", "2026-02-06", "300000.00", "24000.00", "NCC-02"),
            ],
        ),
    )
    return session


def test_sales_summary_totals_the_window_in_decimal(ledger):
    summary = analytics.sales_summary(ledger, date(2026, 1, 1), date(2026, 2, 28))

    assert summary.document_count == 3
    assert summary.customer_count == 2
    assert summary.total == Decimal("3500000.00")
    assert summary.vat_amount == Decimal("280000.00")
    assert all(isinstance(value, Decimal) for value in (summary.total, summary.vat_amount))


def test_sales_are_grouped_by_month(ledger):
    summary = analytics.sales_summary(ledger, date(2026, 1, 1), date(2026, 2, 28))

    assert [(row.month, row.amount, row.document_count) for row in summary.by_month] == [
        ("2026-01", Decimal("3000000.00"), 2),
        ("2026-02", Decimal("500000.00"), 1),
    ]


def test_an_undated_document_is_excluded_from_the_window_and_counted(ledger):
    summary = analytics.sales_summary(ledger, date(2026, 1, 1), date(2026, 2, 28))

    # Excluded from the total, but reported rather than silently dropped.
    assert summary.total == Decimal("3500000.00")
    assert summary.undated_document_count == 1
    assert "999999.00" not in str(summary.total)


def test_purchase_summary_sums_line_vat_for_documents_in_the_window(ledger):
    summary = analytics.purchase_summary(ledger, date(2026, 1, 1), date(2026, 1, 31))

    assert summary.document_count == 1
    assert summary.supplier_count == 1
    assert summary.total == Decimal("700000.00")
    assert summary.vat_amount == Decimal("56000.00")


def test_the_window_bounds_are_inclusive(ledger):
    summary = analytics.sales_summary(ledger, date(2026, 1, 15), date(2026, 1, 15))

    assert summary.document_count == 1
    assert summary.total == Decimal("1000000.00")


def test_an_omitted_window_covers_every_dated_document(ledger):
    summary = analytics.sales_summary(ledger)

    # The undated document is still not in a dated total.
    assert summary.document_count == 4
    assert summary.total == Decimal("4499999.00")


def test_overview_reports_a_delta_that_is_not_called_profit(ledger):
    result = analytics.overview(ledger, date(2026, 1, 1), date(2026, 2, 28))

    assert result.sales.total == Decimal("3500000.00")
    assert result.purchases.total == Decimal("1000000.00")
    assert result.sales_minus_purchases == Decimal("2500000.00")
    assert not hasattr(result, "profit")
    assert not hasattr(result, "gross_profit")


def test_an_inverted_window_is_refused_before_any_query(ledger):
    with pytest.raises(analytics.InvalidDateWindow, match="holds nothing"):
        analytics.sales_summary(ledger, date(2026, 3, 1), date(2026, 1, 1))


def test_an_empty_window_is_zero_not_an_error(ledger):
    summary = analytics.sales_summary(ledger, date(2020, 1, 1), date(2020, 12, 31))

    assert summary.document_count == 0
    assert summary.total == Decimal("0")
    assert summary.by_month == []


def test_overview_endpoint_returns_money_as_decimal_strings(ledger, client):
    response = client.get("/api/analytics/overview?from_date=2026-01-01&to_date=2026-02-28")

    assert response.status_code == 200
    body = response.json()
    assert body["from_date"] == "2026-01-01"
    assert body["sales"]["total"] == "3500000.00"
    assert body["purchases"]["vat_amount"] == "80000.00"
    assert body["sales_minus_purchases"] == "2500000.00"
    # Money must never cross the wire as a JSON float.
    assert isinstance(body["sales"]["total"], str)
    assert isinstance(body["purchases"]["total"], str)


def test_sales_and_purchase_endpoints_answer_separately(ledger, client):
    sales = client.get("/api/analytics/sales?from_date=2026-01-01&to_date=2026-01-31")
    purchases = client.get("/api/analytics/purchases?from_date=2026-01-01&to_date=2026-01-31")

    assert sales.json()["document_count"] == 2
    assert sales.json()["by_month"][0]["month"] == "2026-01"
    assert purchases.json()["supplier_count"] == 1


def test_the_api_refuses_an_inverted_window(ledger, client):
    response = client.get("/api/analytics/overview?from_date=2026-03-01&to_date=2026-01-01")

    assert response.status_code == 422
    assert "holds nothing" in response.json()["detail"]


def test_analytics_needs_a_session_and_any_role_may_read(ledger, anonymous_client, factory_client):
    assert anonymous_client.get("/api/analytics/overview").status_code == 401
    assert factory_client.get("/api/analytics/overview").status_code == 200


def test_analytics_exposes_no_write_route(client):
    for path in ("/api/analytics/overview", "/api/analytics/sales", "/api/analytics/purchases"):
        assert client.post(path, json={}).status_code == 405
