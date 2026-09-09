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
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

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


def _delivered_without_invoice(session: Session) -> list[ExceptionItem]:
    linked = set(session.scalars(select(OrderAccountingLink.order_id)))
    orders = session.scalars(
        select(Order)
        .where(Order.status.in_(DELIVERED_STATES))
        .options(selectinload(Order.customer))
    )
    return [
        ExceptionItem(
            category=ExceptionCategory.DELIVERED_ORDER_NOT_INVOICED,
            reference=order.order_number,
            detail=f"{order.status.value} since {order.required_date} with no linked invoice",
            order_id=order.id,
        )
        for order in orders
        if order.id not in linked
    ]


def _invoices_without_order(session: Session) -> list[ExceptionItem]:
    linked = set(session.scalars(select(OrderAccountingLink.sales_document_id)))
    documents = session.scalars(select(SalesDocument))
    return [
        ExceptionItem(
            category=ExceptionCategory.INVOICE_WITHOUT_ORDER,
            reference=document.invoice_number or document.source_document_number
            or document.source_id,
            detail=(
                f"invoice dated {document.document_date} for "
                f"{document.accounting_object_name or 'unknown customer'} "
                "is not linked to any UniOps order"
            ),
            sales_document_id=document.id,
        )
        for document in documents
        if document.id not in linked
    ]


def _invoices_without_customer_code(session: Session) -> list[ExceptionItem]:
    documents = session.scalars(
        select(SalesDocument).where(SalesDocument.accounting_object_code.is_(None))
    )
    return [
        ExceptionItem(
            category=ExceptionCategory.INVOICE_WITHOUT_CUSTOMER_CODE,
            reference=document.invoice_number or document.source_id,
            detail="no canonical customer code, so it cannot be attributed or matched",
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
                    detail=(
                        f"{len(candidates)} plausible invoices; a person must choose, "
                        "because picking the highest score would state a guess as fact"
                    ),
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
                        f"order customer {code} but invoice customer "
                        f"{document.accounting_object_code}"
                    ),
                    order_id=order.id,
                    sales_document_id=document.id,
                )
            )
        total = order_to_cash.order_total(order)
        if total is not None and total not in (document.subtotal, document.total_amount):
            amount_issues.append(
                ExceptionItem(
                    category=ExceptionCategory.LINKED_AMOUNT_MISMATCH,
                    reference=order.order_number,
                    detail=(
                        f"order total {total} matches neither invoice subtotal "
                        f"{document.subtotal} nor total {document.total_amount}. "
                        "Freight, tax handling, discounts, or a split invoice can "
                        "all explain this; it is evidence, not proof of corruption"
                    ),
                    order_id=order.id,
                    sales_document_id=document.id,
                )
            )
    return customer_issues, amount_issues


def report(session: Session, as_of: date | None = None, limit: int = 50) -> ExceptionReport:
    customer_issues, amount_issues = _linked_disagreements(session)
    collected: list[tuple[ExceptionCategory, list[ExceptionItem]]] = [
        (ExceptionCategory.DELIVERED_ORDER_NOT_INVOICED, _delivered_without_invoice(session)),
        (ExceptionCategory.AMBIGUOUS_INVOICE_CANDIDATES, _ambiguous_candidates(session)),
        (ExceptionCategory.LINKED_CUSTOMER_MISMATCH, customer_issues),
        (ExceptionCategory.LINKED_AMOUNT_MISMATCH, amount_issues),
        (ExceptionCategory.INVOICE_WITHOUT_ORDER, _invoices_without_order(session)),
        (ExceptionCategory.INVOICE_WITHOUT_CUSTOMER_CODE, _invoices_without_customer_code(session)),
    ]
    return ExceptionReport(
        as_of=as_of or date.today(),
        # Every category is always present, so "none found" is visibly none found
        # rather than a category that quietly stopped being computed.
        groups=[
            ExceptionGroup(category=category, count=len(items), items=items[:limit])
            for category, items in collected
        ],
    )
