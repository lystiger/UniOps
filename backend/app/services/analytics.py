"""Mart layer: derived, query-oriented read models over the accounting tables.

This is a read service, not a warehouse. It owns no tables and stores nothing:
every figure is computed from `sales_documents`, `purchase_documents`, and
`purchase_lines` on request. At the current size — hundreds of documents — that
is both fast enough and impossible to get stale, which a materialized table
would not be. Revisit that when a window covers tens of thousands of documents,
not before.

Money is summed in Python with `Decimal` rather than with SQL `SUM`. SQLite has
no native decimal type and aggregates through C doubles, so a SQL sum there is
float arithmetic on money. Summing in the application is exact on every engine
and, at this row count, costs nothing measurable.

Naming is deliberately conservative. `sales_minus_purchases` is exactly what its
name says: it is **not** gross profit and must not be presented as one, because
purchases in a period are not the cost of the goods sold in that period.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PurchaseDocument, PurchaseLine, SalesDocument

ZERO = Decimal("0")


class InvalidDateWindow(ValueError):
    """The requested window cannot contain anything."""


@dataclass(frozen=True)
class MonthlyAmount:
    month: str
    amount: Decimal
    document_count: int


@dataclass(frozen=True)
class SalesSummary:
    document_count: int
    customer_count: int
    total: Decimal
    vat_amount: Decimal
    undated_document_count: int
    by_month: list[MonthlyAmount]


@dataclass(frozen=True)
class PurchaseSummary:
    document_count: int
    supplier_count: int
    total: Decimal
    vat_amount: Decimal
    undated_document_count: int
    by_month: list[MonthlyAmount]


@dataclass(frozen=True)
class CommercialOverview:
    from_date: date | None
    to_date: date | None
    sales: SalesSummary
    purchases: PurchaseSummary
    sales_minus_purchases: Decimal


def check_window(from_date: date | None, to_date: date | None) -> None:
    if from_date and to_date and from_date > to_date:
        raise InvalidDateWindow(
            f"from_date {from_date} is after to_date {to_date}; that window holds nothing"
        )


def _within(statement, column, from_date: date | None, to_date: date | None):
    """Bound a query by document date.

    Undated documents are excluded rather than silently folded into a total: a
    row with no date cannot be shown to belong to the window, and it cannot be
    placed in a month. They are counted separately so their exclusion is visible
    instead of quietly changing the answer.
    """
    if from_date is not None:
        statement = statement.where(column.is_not(None), column >= from_date)
    if to_date is not None:
        statement = statement.where(column.is_not(None), column <= to_date)
    return statement


def _monthly(rows: list[tuple[date, Decimal]]) -> list[MonthlyAmount]:
    totals: defaultdict[str, Decimal] = defaultdict(lambda: ZERO)
    counts: defaultdict[str, int] = defaultdict(int)
    for document_date, amount in rows:
        month = f"{document_date.year:04d}-{document_date.month:02d}"
        totals[month] += amount
        counts[month] += 1
    return [
        MonthlyAmount(month=month, amount=totals[month], document_count=counts[month])
        for month in sorted(totals)
    ]


def _undated(session: Session, model) -> int:
    return len(list(session.scalars(select(model.id).where(model.document_date.is_(None)))))


def sales_summary(
    session: Session, from_date: date | None = None, to_date: date | None = None
) -> SalesSummary:
    check_window(from_date, to_date)
    statement = _within(
        select(
            SalesDocument.document_date,
            SalesDocument.total_amount,
            SalesDocument.vat_amount,
            SalesDocument.accounting_object_code,
        ),
        SalesDocument.document_date,
        from_date,
        to_date,
    )
    rows = list(session.execute(statement))
    total = sum((row.total_amount for row in rows), ZERO)
    vat = sum((row.vat_amount for row in rows), ZERO)
    customers = {row.accounting_object_code for row in rows if row.accounting_object_code}
    dated = [
        (row.document_date, row.total_amount) for row in rows if row.document_date is not None
    ]
    return SalesSummary(
        document_count=len(rows),
        customer_count=len(customers),
        total=total,
        vat_amount=vat,
        undated_document_count=_undated(session, SalesDocument),
        by_month=_monthly(dated),
    )


def purchase_summary(
    session: Session, from_date: date | None = None, to_date: date | None = None
) -> PurchaseSummary:
    check_window(from_date, to_date)
    statement = _within(
        select(
            PurchaseDocument.document_date,
            PurchaseDocument.total_purchase_amount,
            PurchaseDocument.vendor_code,
        ),
        PurchaseDocument.document_date,
        from_date,
        to_date,
    )
    rows = list(session.execute(statement))
    total = sum((row.total_purchase_amount for row in rows), ZERO)
    suppliers = {row.vendor_code for row in rows if row.vendor_code}
    dated = [
        (row.document_date, row.total_purchase_amount)
        for row in rows
        if row.document_date is not None
    ]

    # VAT sits on purchase lines, not on the document, so it is summed from the
    # lines of the documents inside the window. A line whose `thueGTGT` was blank
    # contributes nothing rather than a guessed zero-rate.
    vat_statement = _within(
        select(PurchaseLine.vat_amount).join(
            PurchaseDocument, PurchaseLine.purchase_document_id == PurchaseDocument.id
        ),
        PurchaseDocument.document_date,
        from_date,
        to_date,
    )
    vat = sum((value for value in session.scalars(vat_statement) if value is not None), ZERO)

    return PurchaseSummary(
        document_count=len(rows),
        supplier_count=len(suppliers),
        total=total,
        vat_amount=vat,
        undated_document_count=_undated(session, PurchaseDocument),
        by_month=_monthly(dated),
    )


def overview(
    session: Session, from_date: date | None = None, to_date: date | None = None
) -> CommercialOverview:
    check_window(from_date, to_date)
    sales = sales_summary(session, from_date, to_date)
    purchases = purchase_summary(session, from_date, to_date)
    return CommercialOverview(
        from_date=from_date,
        to_date=to_date,
        sales=sales,
        purchases=purchases,
        # Gross commercial flow, not profit: these purchases are not the cost of
        # these sales, and no period matching has been done.
        sales_minus_purchases=sales.total - purchases.total,
    )
