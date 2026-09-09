"""The validate/reconcile stage of the ingestion pipeline.

Extract -> raw -> normalize -> **reconcile** -> publish.

Two kinds of check live here. Document reconciliation compares what EasyBooks
says about a document against what its own lines say. Pipeline integrity checks
the shape of what was published: no orphan lines, no document that lost its
lineage back to a raw payload.

Neither check invents a guarantee EasyBooks does not give. A purchase document's
total is computed by summing its own rows, so comparing the two would prove
nothing and is deliberately absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations.easybooks.contracts import SalesDocumentRecord, SalesLineRecord
from app.models import (
    Customer,
    Order,
    OrderAccountingLink,
    PurchaseDocument,
    PurchaseLine,
    SalesDocument,
    SalesLine,
)

# Money arrives already rounded by EasyBooks, so a sub-unit difference is
# rounding rather than a disagreement worth a person's attention.
DEFAULT_TOLERANCE = Decimal("1")


def reconcile_sales(
    document: SalesDocumentRecord,
    lines: list[SalesLineRecord],
    tolerance: Decimal = DEFAULT_TOLERANCE,
) -> list[str]:
    """Compare a sales header against its detail lines. Warns, never discards."""
    line_amount = sum((line.amount for line in lines), Decimal("0"))
    line_vat = sum((line.vat_amount for line in lines), Decimal("0"))
    calculated_total = document.subtotal - document.discount_amount + document.vat_amount
    checks = (
        ("line subtotal", line_amount, document.subtotal),
        ("line VAT", line_vat, document.vat_amount),
        ("header total", calculated_total, document.total_amount),
    )
    return [
        f"{label} differs by {actual - expected}"
        for label, actual, expected in checks
        if abs(actual - expected) > tolerance
    ]


@dataclass(frozen=True)
class IntegrityReport:
    orphan_sales_lines: int
    orphan_purchase_lines: int
    sales_documents_without_lineage: int
    purchase_documents_without_lineage: int
    orphan_accounting_links: int = 0
    accounting_links_with_customer_mismatch: int = 0

    @property
    def warnings(self) -> list[str]:
        found = []
        if self.orphan_accounting_links:
            found.append(
                f"{self.orphan_accounting_links} order-invoice links point at an "
                "order or sales document that no longer exists"
            )
        if self.accounting_links_with_customer_mismatch:
            found.append(
                f"{self.accounting_links_with_customer_mismatch} order-invoice links "
                "join an order and an invoice belonging to different customers"
            )
        if self.orphan_sales_lines:
            found.append(f"{self.orphan_sales_lines} sales lines have no parent document")
        if self.orphan_purchase_lines:
            found.append(f"{self.orphan_purchase_lines} purchase lines have no parent document")
        if self.sales_documents_without_lineage:
            found.append(
                f"{self.sales_documents_without_lineage} sales documents have no raw lineage"
            )
        if self.purchase_documents_without_lineage:
            found.append(
                f"{self.purchase_documents_without_lineage} purchase documents "
                "have no raw lineage"
            )
        return found


def check_integrity(session: Session) -> IntegrityReport:
    """Check the published accounting layer for breaks a source read cannot cause.

    SQLite does not enforce foreign keys unless asked to, so an orphan line is
    detectable there in a way PostgreSQL would have refused outright. Running the
    check on both means the invariant is stated once and holds everywhere.
    """

    def _orphans(line_model, document_model, join_column) -> int:
        return session.scalar(
            select(func.count())
            .select_from(line_model)
            .where(
                ~select(document_model.id)
                .where(document_model.id == join_column)
                .exists()
            )
        )

    def _missing_lineage(model) -> int:
        return session.scalar(
            select(func.count()).select_from(model).where(model.source_raw_record_id.is_(None))
        )

    # A link whose two sides name different customers is a genuine break: one of
    # them is wrong. Neither side is rewritten - the warning names it and a person
    # decides, because silently "correcting" accounting lineage is how a wrong
    # answer becomes an invisible one.
    mismatched = session.scalar(
        select(func.count())
        .select_from(OrderAccountingLink)
        .join(Order, Order.id == OrderAccountingLink.order_id)
        .join(Customer, Customer.id == Order.customer_id)
        .join(SalesDocument, SalesDocument.id == OrderAccountingLink.sales_document_id)
        .where(
            Customer.easybooks_accounting_object_code.is_not(None),
            SalesDocument.accounting_object_code.is_not(None),
            Customer.easybooks_accounting_object_code != SalesDocument.accounting_object_code,
        )
    )

    return IntegrityReport(
        orphan_sales_lines=_orphans(SalesLine, SalesDocument, SalesLine.sales_document_id),
        orphan_purchase_lines=_orphans(
            PurchaseLine, PurchaseDocument, PurchaseLine.purchase_document_id
        ),
        sales_documents_without_lineage=_missing_lineage(SalesDocument),
        purchase_documents_without_lineage=_missing_lineage(PurchaseDocument),
        orphan_accounting_links=(
            _orphans(OrderAccountingLink, Order, OrderAccountingLink.order_id)
            + _orphans(
                OrderAccountingLink, SalesDocument, OrderAccountingLink.sales_document_id
            )
        ),
        accounting_links_with_customer_mismatch=mismatched,
    )
