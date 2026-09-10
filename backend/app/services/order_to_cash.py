"""Order-to-cash: which UniOps order became which EasyBooks invoice.

```text
ORDER -> DELIVERY -> EASYBOOKS SALES INVOICE -> RECEIVABLE -> PAYMENT
```

UniOps owns the order and the link. EasyBooks owns the invoice and every
accounting fact about it. Linking transfers no ownership: it records a belief
about a relationship EasyBooks does not model, and nothing here writes to
EasyBooks.

**What the source supports today.** The observed sales payloads carry an invoice
id, number, series, date, customer code, and money. They carry no due date, no
paid amount, no outstanding amount, and no payment reference: `mbDepositID` and
`mcReceiptID` are null on all 111 observed documents. So `INVOICED` is derivable
and every payment-derived state is honestly `UNKNOWN` until a payment source is
observed and ingested. Nothing here approximates a balance or a due date.

Every accounting state is derived at query time. None is stored, so an EasyBooks
correction cannot leave a stale flag behind.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    LinkMethod,
    Order,
    OrderAccountingLink,
    OrderStatus,
    SalesDocument,
    User,
)

ZERO = Decimal("0")

# How far an invoice date may sit from the order's required date and still be
# considered the same commercial event. Seven days matches the sync window
# already used for overlapping live reads.
CANDIDATE_WINDOW_DAYS = 7
# A single candidate at or above this score, with the amount agreeing, is the
# only shape that would justify an automatic link.
AUTO_LINK_CONFIDENCE = Decimal("0.95")


class AccountingStatus(StrEnum):
    NOT_INVOICED = "NOT_INVOICED"
    INVOICE_CANDIDATE = "INVOICE_CANDIDATE"
    INVOICED = "INVOICED"


class PaymentStatus(StrEnum):
    """Only UNKNOWN is reachable today.

    The other members are declared so the read model has somewhere to go the day
    a payment source is observed. Nothing returns them, and no test asserts them,
    because no observed EasyBooks field supports the distinction.
    """

    UNKNOWN = "UNKNOWN"
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"


class DueStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    DUE = "DUE"
    OVERDUE = "OVERDUE"


class LinkError(ValueError):
    pass


class LinkNotFound(LookupError):
    pass


# Stated once, used everywhere a payment-derived figure would otherwise be
# invented. Changing this string means a payment source arrived.
NO_PAYMENT_SOURCE = (
    "EasyBooks exposes no paid or outstanding amount on any observed sales "
    "document, and no payment source has been ingested"
)
NO_DUE_DATE_SOURCE = "EasyBooks exposes no due date on any observed sales document"


@dataclass(frozen=True)
class InvoiceCandidate:
    sales_document_id: str
    source_id: str
    invoice_number: str | None
    invoice_series: str | None
    document_date: date | None
    subtotal: Decimal
    total_amount: Decimal
    confidence: Decimal
    evidence: dict[str, Any]


@dataclass(frozen=True)
class LinkedInvoice:
    link_id: str
    sales_document_id: str
    source_id: str
    invoice_number: str | None
    invoice_series: str | None
    document_date: date | None
    subtotal: Decimal
    total_amount: Decimal
    vat_amount: Decimal
    link_method: LinkMethod
    confidence: Decimal | None
    evidence: dict[str, Any] | None
    created_by: str | None
    payment_status: PaymentStatus
    due_date: date | None
    due_status: DueStatus


@dataclass(frozen=True)
class OrderAccounting:
    order_id: str
    order_number: str
    lifecycle_status: str
    order_total: Decimal | None
    accounting_status: AccountingStatus
    payment_status: PaymentStatus
    outstanding_amount: Decimal | None
    outstanding_status: str
    invoices: list[LinkedInvoice] = field(default_factory=list)
    candidate_count: int = 0


def order_total(order: Order) -> Decimal | None:
    """What the order says it is worth, or None if it does not say.

    A line without an agreed price makes the order's value unknown. Treating a
    missing price as zero would silently understate the order and then "match" an
    invoice it does not match.
    """
    total = ZERO
    for line in order.lines:
        if line.agreed_unit_price is None:
            return None
        total += line.quantity * line.agreed_unit_price
    return total


def _customer_code(order: Order) -> str | None:
    return order.customer.easybooks_accounting_object_code if order.customer else None


def _score(evidence: dict[str, Any]) -> Decimal:
    """Deterministic and explainable. No model, no learning, no hidden weights.

    The customer code is the floor: without it there is no candidate at all. The
    amount is what makes a match believable, and date proximity only breaks ties.
    """
    score = Decimal("0.50")  # customer code agreed
    if evidence.get("amount_match"):
        score += Decimal("0.40")
    difference = evidence.get("date_difference_days")
    if difference is not None:
        if difference <= 1:
            score += Decimal("0.10")
        elif difference <= CANDIDATE_WINDOW_DAYS:
            score += Decimal("0.05")
    return min(score, Decimal("1.0"))


def _evidence(order: Order, document: SalesDocument) -> dict[str, Any]:
    total = order_total(order)
    matched = total is not None and total in (document.subtotal, document.total_amount)
    difference = None
    if document.document_date is not None:
        difference = abs((document.document_date - order.required_date).days)
    return {
        "customer_code": _customer_code(order),
        "customer_code_match": True,
        "order_total": str(total) if total is not None else None,
        "invoice_subtotal": str(document.subtotal),
        "invoice_total": str(document.total_amount),
        # False also when the order carries no priced lines: unknown is not a match.
        "amount_match": matched,
        "date_difference_days": difference,
    }


def invoice_candidates(session: Session, order: Order) -> list[InvoiceCandidate]:
    """Invoices that could plausibly be this order, scored and explained.

    Candidacy requires the canonical customer code to agree. An order whose
    customer has no EasyBooks code has no candidates, rather than every invoice
    in the window.
    """
    code = _customer_code(order)
    if not code:
        return []
    linked = set(
        session.scalars(
            select(OrderAccountingLink.sales_document_id).where(
                OrderAccountingLink.order_id == order.id
            )
        )
    )
    documents = session.scalars(
        select(SalesDocument).where(SalesDocument.accounting_object_code == code)
    )
    candidates = []
    for document in documents:
        if document.id in linked:
            continue
        evidence = _evidence(order, document)
        difference = evidence["date_difference_days"]
        if difference is None or difference > CANDIDATE_WINDOW_DAYS:
            continue
        candidates.append(
            InvoiceCandidate(
                sales_document_id=document.id,
                source_id=document.source_id,
                invoice_number=document.invoice_number,
                invoice_series=document.invoice_series,
                document_date=document.document_date,
                subtotal=document.subtotal,
                total_amount=document.total_amount,
                confidence=_score(evidence),
                evidence=evidence,
            )
        )
    return sorted(candidates, key=lambda c: (-c.confidence, c.source_id))


def auto_linkable(candidates: list[InvoiceCandidate]) -> InvoiceCandidate | None:
    """The one candidate strong enough to link without a person, or nothing.

    Two plausible invoices means the answer is unknown, and an unknown accounting
    link presented as certain is worse than no link. Ambiguity is returned to a
    human rather than resolved by picking the highest score.
    """
    if len(candidates) != 1:
        return None
    only = candidates[0]
    if only.evidence.get("amount_match") and only.confidence >= AUTO_LINK_CONFIDENCE:
        return only
    return None


def _method_for(evidence: dict[str, Any], confidence: Decimal) -> LinkMethod:
    if evidence.get("amount_match") and confidence >= AUTO_LINK_CONFIDENCE:
        return LinkMethod.CUSTOMER_DATE_AMOUNT
    return LinkMethod.MANUAL


def create_link(
    session: Session, order: Order, sales_document_id: str, user: User
) -> OrderAccountingLink:
    """Record that a person says this order became this invoice.

    The evidence is recomputed for the chosen pair and stored with it, so a link
    that a person made against weak evidence still says so afterwards.
    """
    if order.status == OrderStatus.CANCELLED:
        raise LinkError("cannot link an invoice to a cancelled order")
    document = session.get(SalesDocument, sales_document_id)
    if document is None:
        raise LinkNotFound("sales document not found")
    existing = session.scalar(
        select(OrderAccountingLink).where(
            OrderAccountingLink.order_id == order.id,
            OrderAccountingLink.sales_document_id == sales_document_id,
        )
    )
    if existing is not None:
        raise LinkError("this order is already linked to that invoice")

    evidence = _evidence(order, document)
    evidence["customer_code_match"] = (
        _customer_code(order) is not None
        and _customer_code(order) == document.accounting_object_code
    )
    confidence = _score(evidence) if evidence["customer_code_match"] else None
    link = OrderAccountingLink(
        order_id=order.id,
        sales_document_id=sales_document_id,
        link_method=_method_for(evidence, confidence) if confidence else LinkMethod.MANUAL,
        confidence=confidence,
        evidence=evidence,
        created_by_user_id=user.id,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def delete_link(session: Session, order: Order, link_id: str) -> None:
    """Remove the UniOps relationship only. EasyBooks is not touched."""
    link = session.scalar(
        select(OrderAccountingLink).where(
            OrderAccountingLink.id == link_id, OrderAccountingLink.order_id == order.id
        )
    )
    if link is None:
        raise LinkNotFound("link not found for this order")
    session.delete(link)
    session.commit()


def _linked_invoice(link: OrderAccountingLink) -> LinkedInvoice:
    document = link.sales_document
    return LinkedInvoice(
        link_id=link.id,
        sales_document_id=document.id,
        source_id=document.source_id,
        invoice_number=document.invoice_number,
        invoice_series=document.invoice_series,
        document_date=document.document_date,
        subtotal=document.subtotal,
        total_amount=document.total_amount,
        vat_amount=document.vat_amount,
        link_method=link.link_method,
        confidence=link.confidence,
        evidence=link.evidence,
        created_by=link.created_by.username if link.created_by else None,
        # No observed field supports either. Reported as unknown, never guessed.
        payment_status=PaymentStatus.UNKNOWN,
        due_date=None,
        due_status=DueStatus.UNKNOWN,
    )


def links_for(session: Session, order_id: str) -> list[OrderAccountingLink]:
    return list(
        session.scalars(
            select(OrderAccountingLink)
            .where(OrderAccountingLink.order_id == order_id)
            .options(
                selectinload(OrderAccountingLink.sales_document),
                selectinload(OrderAccountingLink.created_by),
            )
            .order_by(OrderAccountingLink.created_at)
        )
    )


def accounting_for(session: Session, order: Order) -> OrderAccounting:
    """The full accounting picture of one order, derived, nothing stored."""
    links = links_for(session, order.id)
    invoices = [_linked_invoice(link) for link in links]
    candidate_count = 0 if invoices else len(invoice_candidates(session, order))
    if invoices:
        status = AccountingStatus.INVOICED
    elif candidate_count:
        status = AccountingStatus.INVOICE_CANDIDATE
    else:
        status = AccountingStatus.NOT_INVOICED
    return OrderAccounting(
        order_id=order.id,
        order_number=order.order_number,
        lifecycle_status=order.status.value,
        order_total=order_total(order),
        accounting_status=status,
        payment_status=PaymentStatus.UNKNOWN,
        outstanding_amount=None,
        outstanding_status=NO_PAYMENT_SOURCE,
        invoices=invoices,
        candidate_count=candidate_count,
    )


def accounting_status_by_order(session: Session, orders: list[Order]) -> dict[str, str]:
    """Bulk status for the board: two queries for the whole page, not two per card.

    It answers the same three states the detail view does, so a card and the
    panel behind it never disagree.
    """
    if not orders:
        return {}
    order_ids = [order.id for order in orders]
    linked = set(
        session.scalars(
            select(OrderAccountingLink.order_id).where(
                OrderAccountingLink.order_id.in_(order_ids)
            )
        )
    )
    unlinked = [order for order in orders if order.id not in linked]
    codes = {code for order in unlinked if (code := _customer_code(order))}
    by_code: dict[str, list[SalesDocument]] = {}
    if codes:
        for document in session.scalars(
            select(SalesDocument).where(SalesDocument.accounting_object_code.in_(codes))
        ):
            by_code.setdefault(document.accounting_object_code, []).append(document)

    statuses = {order_id: AccountingStatus.INVOICED.value for order_id in linked}
    for order in unlinked:
        code = _customer_code(order)
        near = any(
            document.document_date is not None
            and abs((document.document_date - order.required_date).days)
            <= CANDIDATE_WINDOW_DAYS
            for document in by_code.get(code, [])
        )
        statuses[order.id] = (
            AccountingStatus.INVOICE_CANDIDATE.value
            if near
            else AccountingStatus.NOT_INVOICED.value
        )
    return statuses
