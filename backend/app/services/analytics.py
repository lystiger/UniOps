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


# --- Receivables -----------------------------------------------------------
#
# A receivable here is a *derived read model over EasyBooks data*, not a second
# ledger. Nothing below is stored, so an EasyBooks correction changes the answer
# on the next request rather than leaving a stale total behind.
#
# What the source supports: every observed sales document posts its lines to
# debit account 131 - Phai thu khach hang, Vietnamese for accounts receivable -
# and all 111 carry typeID 320, "Ban hang chua thu tien", a sale on credit. So a
# receivable demonstrably *exists* for each invoice. What EasyBooks does not
# expose anywhere in the observed payloads is whether it has since been settled:
# no paid amount, no outstanding amount, no due date, and `mbDepositID` and
# `mcReceiptID` null on every document.
#
# Following the project's rule that an invented balance is worse than an absent
# one, outstanding and overdue are reported as unknown rather than as zero.
# Reporting 0.00 would assert that everything has been paid, which is a claim the
# data does not make.


@dataclass(frozen=True)
class CustomerReceivable:
    customer_id: str | None
    customer_code: str
    customer_name: str | None
    invoice_count: int
    total_invoiced: Decimal
    oldest_invoice_date: date | None
    newest_invoice_date: date | None
    outstanding_amount: Decimal | None
    overdue_amount: Decimal | None


@dataclass(frozen=True)
class ReceivablesSummary:
    as_of: date
    from_date: date | None
    to_date: date | None
    total_invoiced: Decimal
    invoice_count: int
    linked_invoice_count: int
    unlinked_invoice_count: int
    total_outstanding: Decimal | None
    total_overdue: Decimal | None
    unpaid_invoice_count: int | None
    overdue_invoice_count: int | None
    outstanding_status: str
    due_status: str
    customers: list[CustomerReceivable]


def receivables(
    session: Session,
    as_of: date | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> ReceivablesSummary:
    from app.models import Customer, OrderAccountingLink
    from app.services.order_to_cash import NO_DUE_DATE_SOURCE, NO_PAYMENT_SOURCE

    check_window(from_date, to_date)
    as_of = as_of or date.today()

    statement = _within(
        select(
            SalesDocument.id,
            SalesDocument.document_date,
            SalesDocument.total_amount,
            SalesDocument.accounting_object_code,
            SalesDocument.accounting_object_name,
        ),
        SalesDocument.document_date,
        from_date,
        to_date,
    )
    rows = list(session.execute(statement))
    linked_ids = set(session.scalars(select(OrderAccountingLink.sales_document_id)))

    codes = {row.accounting_object_code for row in rows if row.accounting_object_code}
    customers = {
        customer.easybooks_accounting_object_code: customer
        for customer in session.scalars(
            select(Customer).where(Customer.easybooks_accounting_object_code.in_(codes or {""}))
        )
    }

    grouped: defaultdict[str, list] = defaultdict(list)
    for row in rows:
        # An invoice with no customer code cannot be owed by anybody in
        # particular. It is counted in the total and reported as an exception
        # rather than attributed to a guess.
        if row.accounting_object_code:
            grouped[row.accounting_object_code].append(row)

    per_customer = []
    for code in sorted(grouped):
        entries = grouped[code]
        dates = [entry.document_date for entry in entries if entry.document_date]
        customer = customers.get(code)
        per_customer.append(
            CustomerReceivable(
                customer_id=customer.id if customer else None,
                customer_code=code,
                customer_name=(
                    customer.name if customer else entries[0].accounting_object_name
                ),
                invoice_count=len(entries),
                total_invoiced=sum((entry.total_amount for entry in entries), ZERO),
                oldest_invoice_date=min(dates) if dates else None,
                newest_invoice_date=max(dates) if dates else None,
                outstanding_amount=None,
                overdue_amount=None,
            )
        )

    linked = sum(1 for row in rows if row.id in linked_ids)
    return ReceivablesSummary(
        as_of=as_of,
        from_date=from_date,
        to_date=to_date,
        total_invoiced=sum((row.total_amount for row in rows), ZERO),
        invoice_count=len(rows),
        linked_invoice_count=linked,
        unlinked_invoice_count=len(rows) - linked,
        total_outstanding=None,
        total_overdue=None,
        unpaid_invoice_count=None,
        overdue_invoice_count=None,
        outstanding_status=NO_PAYMENT_SOURCE,
        due_status=NO_DUE_DATE_SOURCE,
        customers=per_customer,
    )


@dataclass(frozen=True)
class CustomerInvoice:
    sales_document_id: str
    invoice_number: str | None
    invoice_series: str | None
    document_date: date | None
    total_amount: Decimal
    vat_amount: Decimal
    paid_amount: Decimal | None
    outstanding_amount: Decimal | None
    payment_status: str
    due_date: date | None
    due_status: str
    linked_order_numbers: list[str]


@dataclass(frozen=True)
class CustomerReceivableDetail:
    customer_id: str
    customer_name: str
    customer_code: str | None
    as_of: date
    invoice_count: int
    total_invoiced: Decimal
    oldest_invoice_date: date | None
    total_outstanding: Decimal | None
    overdue_amount: Decimal | None
    outstanding_status: str
    due_status: str
    invoices: list[CustomerInvoice]


class CustomerNotFound(LookupError):
    pass


def customer_receivable(
    session: Session, customer_id: str, as_of: date | None = None
) -> CustomerReceivableDetail:
    """One customer's invoices, with the UniOps orders each is linked to.

    Invoices are found through the canonical customer code, which is what links
    an EasyBooks document to a UniOps customer. A customer without a code has no
    invoices to show rather than somebody else's.
    """
    from app.models import Customer, Order, OrderAccountingLink
    from app.services.order_to_cash import (
        NO_DUE_DATE_SOURCE,
        NO_PAYMENT_SOURCE,
        DueStatus,
        PaymentStatus,
    )

    customer = session.get(Customer, customer_id)
    if customer is None:
        raise CustomerNotFound("customer not found")
    as_of = as_of or date.today()
    code = customer.easybooks_accounting_object_code

    documents = (
        list(
            session.scalars(
                select(SalesDocument)
                .where(SalesDocument.accounting_object_code == code)
                .order_by(SalesDocument.document_date)
            )
        )
        if code
        else []
    )
    orders_by_document: defaultdict[str, list[str]] = defaultdict(list)
    if documents:
        rows = session.execute(
            select(OrderAccountingLink.sales_document_id, Order.order_number)
            .join(Order, Order.id == OrderAccountingLink.order_id)
            .where(
                OrderAccountingLink.sales_document_id.in_([d.id for d in documents])
            )
        )
        for document_id, order_number in rows:
            orders_by_document[document_id].append(order_number)

    invoices = [
        CustomerInvoice(
            sales_document_id=document.id,
            invoice_number=document.invoice_number,
            invoice_series=document.invoice_series,
            document_date=document.document_date,
            total_amount=document.total_amount,
            vat_amount=document.vat_amount,
            # No observed EasyBooks field carries either figure.
            paid_amount=None,
            outstanding_amount=None,
            payment_status=PaymentStatus.UNKNOWN.value,
            due_date=None,
            due_status=DueStatus.UNKNOWN.value,
            linked_order_numbers=sorted(orders_by_document.get(document.id, [])),
        )
        for document in documents
    ]
    dates = [d.document_date for d in documents if d.document_date]
    return CustomerReceivableDetail(
        customer_id=customer.id,
        customer_name=customer.name,
        customer_code=code,
        as_of=as_of,
        invoice_count=len(documents),
        total_invoiced=sum((d.total_amount for d in documents), ZERO),
        oldest_invoice_date=min(dates) if dates else None,
        total_outstanding=None,
        overdue_amount=None,
        outstanding_status=NO_PAYMENT_SOURCE,
        due_status=NO_DUE_DATE_SOURCE,
        invoices=invoices,
    )
