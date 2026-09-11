"""Operational exceptions: where the order flow and the accounting record disagree.

Explicit categories, no severity scoring. Each one is a question somebody in the
office would actually ask, and each returns the rows that answer it rather than a
count to be trusted on faith.

Categories that would depend on payment or due-date data are deliberately absent
rather than approximated: EasyBooks exposes neither on any observed document.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.integrations.easybooks.client import business_today
from app.models import Order, OrderAccountingLink, OrderStatus, SalesDocument
from app.services import order_to_cash

# Lifecycle states in which an invoice should already exist.
DELIVERED_STATES = (OrderStatus.DELIVERED, OrderStatus.INVOICED, OrderStatus.CLOSED)


class ExceptionCategory(StrEnum):
    DELIVERED_ORDER_NOT_INVOICED = "DELIVERED_ORDER_NOT_INVOICED"
    INVOICE_WITHOUT_ORDER = "INVOICE_WITHOUT_ORDER"
    AMBIGUOUS_INVOICE_CANDIDATES = "AMBIGUOUS_INVOICE_CANDIDATES"
    LINKED_CUSTOMER_MISMATCH = "LINKED_CUSTOMER_MISMATCH"
    LINKED_AMOUNT_MISMATCH = "LINKED_AMOUNT_MISMATCH"
    INVOICE_WITHOUT_CUSTOMER_CODE = "INVOICE_WITHOUT_CUSTOMER_CODE"


@dataclass(frozen=True)
class ExceptionItem:
    category: ExceptionCategory
    reference: str
    detail: str
    customer_name: str | None = None
    document_date: date | None = None
    total_amount: Decimal | None = None
    order_total: Decimal | None = None
    invoice_subtotal: Decimal | None = None
    order_id: str | None = None
    sales_document_id: str | None = None


@dataclass(frozen=True)
class ExceptionGroup:
    category: ExceptionCategory
    count: int
    items: list[ExceptionItem] = field(default_factory=list)


@dataclass(frozen=True)
class ExceptionReport:
    as_of: date
    groups: list[ExceptionGroup]

    @property
    def total(self) -> int:
        return sum(group.count for group in self.groups)


def _format_invoice_ref(doc: SalesDocument) -> str:
    # The identifier alone: the UI says what kind of reference it is, in the reader's language.
    if doc.invoice_series and doc.invoice_number:
        return f"{doc.invoice_series}/{doc.invoice_number}"
    if doc.invoice_number:
        return doc.invoice_number
    return doc.source_document_number or doc.source_id


def _delivered_without_invoice(session: Session) -> list[ExceptionItem]:
    linked = set(session.scalars(select(OrderAccountingLink.order_id)))
    orders = session.scalars(
        select(Order)
        .where(Order.status.in_(DELIVERED_STATES))
        .options(selectinload(Order.customer), selectinload(Order.lines))
    )
    return [
        ExceptionItem(
            category=ExceptionCategory.DELIVERED_ORDER_NOT_INVOICED,
            reference=order.order_number,
            detail=f"{order.status.value} order has no linked invoice",
            customer_name=order.customer.name if order.customer else None,
            document_date=order.required_date,
            total_amount=order_to_cash.order_total(order),
            order_id=order.id,
        )
        for order in orders
        if order.id not in linked
    ]


def _invoices_without_order(
    session: Session, order_tracking_since: date | None = None
) -> list[ExceptionItem]:
    linked = set(session.scalars(select(OrderAccountingLink.sales_document_id)))
    documents = session.scalars(
        select(SalesDocument).order_by(SalesDocument.document_date.desc().nullslast())
    )
    found = []
    for document in documents:
        if document.id in linked:
            continue
        if (
            order_tracking_since is not None
            and document.document_date is not None
            and document.document_date < order_tracking_since
        ):
            continue
        found.append(
            ExceptionItem(
                category=ExceptionCategory.INVOICE_WITHOUT_ORDER,
                reference=_format_invoice_ref(document),
                detail="Invoice not linked to any UniOps order",
                customer_name=document.accounting_object_name,
                document_date=document.document_date,
                total_amount=document.total_amount,
                sales_document_id=document.id,
            )
        )
    return found


def _invoices_without_customer_code(session: Session) -> list[ExceptionItem]:
    documents = session.scalars(
        select(SalesDocument)
        .where(SalesDocument.accounting_object_code.is_(None))
        .order_by(SalesDocument.document_date.desc().nullslast())
    )
    return [
        ExceptionItem(
            category=ExceptionCategory.INVOICE_WITHOUT_CUSTOMER_CODE,
            reference=_format_invoice_ref(document),
            detail="No canonical customer code; cannot be attributed or matched",
            customer_name=document.accounting_object_name,
            document_date=document.document_date,
            total_amount=document.total_amount,
            sales_document_id=document.id,
        )
        for document in documents
    ]


def _ambiguous_candidates(session: Session) -> list[ExceptionItem]:
    """Orders where more than one invoice is plausible, so nothing may be linked."""
    linked = set(session.scalars(select(OrderAccountingLink.order_id)))
    orders = session.scalars(
        select(Order)
        .where(Order.status.in_(DELIVERED_STATES))
        .options(selectinload(Order.customer), selectinload(Order.lines))
    )
    found = []
    for order in orders:
        if order.id in linked:
            continue
        candidates = order_to_cash.invoice_candidates(session, order)
        if len(candidates) > 1:
            found.append(
                ExceptionItem(
                    category=ExceptionCategory.AMBIGUOUS_INVOICE_CANDIDATES,
                    reference=order.order_number,
                    detail=f"{len(candidates)} plausible invoices require manual selection",
                    customer_name=order.customer.name if order.customer else None,
                    document_date=order.required_date,
                    total_amount=order_to_cash.order_total(order),
                    order_id=order.id,
                )
            )
    return found


def _linked_disagreements(session: Session) -> tuple[list[ExceptionItem], list[ExceptionItem]]:
    """Links whose two sides disagree. Reported as evidence, never rewritten."""
    links = session.scalars(
        select(OrderAccountingLink).options(
            selectinload(OrderAccountingLink.order).selectinload(Order.customer),
            selectinload(OrderAccountingLink.order).selectinload(Order.lines),
            selectinload(OrderAccountingLink.sales_document),
        )
    )
    customer_issues, amount_issues = [], []
    for link in links:
        order, document = link.order, link.sales_document
        code = order.customer.easybooks_accounting_object_code if order.customer else None
        if code and document.accounting_object_code and code != document.accounting_object_code:
            customer_issues.append(
                ExceptionItem(
                    category=ExceptionCategory.LINKED_CUSTOMER_MISMATCH,
                    reference=order.order_number,
                    detail=(
                        f"Order customer ({code}) differs from invoice customer "
                        f"({document.accounting_object_code})"
                    ),
                    customer_name=order.customer.name if order.customer else None,
                    document_date=order.required_date,
                    total_amount=document.total_amount,
                    order_id=order.id,
                    sales_document_id=document.id,
                )
            )
        total = order_to_cash.order_total(order)
        if total is not None and total not in (document.subtotal, document.total_amount):
            def _format_vnd(val: Decimal | None) -> str:
                if val is None:
                    return "—"
                return f"{val:,.0f} ₫".replace(",", ".")

            subtotal_fmt = _format_vnd(document.subtotal)
            invoice_total_fmt = _format_vnd(document.total_amount)
            order_total_fmt = _format_vnd(total)

            amount_issues.append(
                ExceptionItem(
                    category=ExceptionCategory.LINKED_AMOUNT_MISMATCH,
                    reference=order.order_number,
                    detail=(
                        f"Order total {order_total_fmt} matches neither invoice subtotal "
                        f"{subtotal_fmt} nor total {invoice_total_fmt}"
                    ),
                    customer_name=order.customer.name if order.customer else None,
                    document_date=order.required_date,
                    total_amount=document.total_amount,
                    order_total=total,
                    invoice_subtotal=document.subtotal,
                    order_id=order.id,
                    sales_document_id=document.id,
                )
            )
    return customer_issues, amount_issues


def report(
    session: Session,
    as_of: date | None = None,
    limit: int = 50,
    order_tracking_since: date | None = None,
) -> ExceptionReport:
    if as_of is None:
        as_of = business_today()
    if order_tracking_since is None:
        order_tracking_since = get_settings().order_tracking_since

    customer_issues, amount_issues = _linked_disagreements(session)
    collected: list[tuple[ExceptionCategory, list[ExceptionItem]]] = [
        (ExceptionCategory.DELIVERED_ORDER_NOT_INVOICED, _delivered_without_invoice(session)),
        (ExceptionCategory.AMBIGUOUS_INVOICE_CANDIDATES, _ambiguous_candidates(session)),
        (ExceptionCategory.LINKED_CUSTOMER_MISMATCH, customer_issues),
        (ExceptionCategory.LINKED_AMOUNT_MISMATCH, amount_issues),
        (
            ExceptionCategory.INVOICE_WITHOUT_ORDER,
            _invoices_without_order(session, order_tracking_since=order_tracking_since),
        ),
        (
            ExceptionCategory.INVOICE_WITHOUT_CUSTOMER_CODE,
            _invoices_without_customer_code(session),
        ),
    ]
    return ExceptionReport(
        as_of=as_of,
        # Every category is always present, so "none found" is visibly none found
        # rather than a category that quietly stopped being computed.
        groups=[
            ExceptionGroup(category=category, count=len(items), items=items[:limit])
            for category, items in collected
        ],
    )
