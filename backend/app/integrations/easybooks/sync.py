from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.integrations.easybooks.client import EasyBooksClient
from app.integrations.easybooks.normalization import (
    group_purchase_rows,
    normalize_purchase_document,
    normalize_purchase_lines,
    normalize_sales_document,
    normalize_sales_lines,
    payload_hash,
    reconcile_sales,
)
from app.models import (
    Customer,
    EasyBooksRawRecord,
    EasyBooksSyncRun,
    Product,
    PurchaseDocument,
    PurchaseLine,
    SalesDocument,
    SalesLine,
    SyncStatus,
    utc_now,
)

logger = logging.getLogger(__name__)


@dataclass
class FixtureBundle:
    sales_documents: list[dict[str, Any]] = field(default_factory=list)
    sales_lines: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    purchase_rows: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FixtureBundle:
        documents = payload.get("sales_documents", [])
        lines = payload.get("sales_lines", {})
        purchases = payload.get("purchase_rows", [])
        if (
            not isinstance(documents, list)
            or not isinstance(lines, dict)
            or not isinstance(purchases, list)
        ):
            raise ValueError(
                "fixture requires sales_documents list, sales_lines object, and purchase_rows list"
            )
        return cls(documents, lines, purchases)


def _extract_rows(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        for key in ("data", "result", "items", "content"):
            candidate = response.get(key)
            if isinstance(candidate, list):
                return candidate
            if isinstance(candidate, dict):
                nested = _extract_rows(candidate)
                if nested:
                    return nested
    raise ValueError("EasyBooks response did not contain a row list")


def fetch_live_bundle(client: EasyBooksClient, from_date: date, to_date: date) -> FixtureBundle:
    """Read known endpoints only; no endpoint discovery or write calls."""
    documents = _extract_rows(client.sales_documents(from_date, to_date))
    sales_lines = {
        str(document["id"]): _extract_rows(client.sales_lines(str(document["id"])))
        for document in documents
    }
    purchase_rows = _extract_rows(client.purchase_report(from_date, to_date))
    return FixtureBundle(documents, sales_lines, purchase_rows)


def _preserve_raw(
    session: Session,
    run: EasyBooksSyncRun,
    entity_type: str,
    source_id: str,
    payload: dict[str, Any] | list[Any],
) -> bool:
    digest = payload_hash(payload)
    exists = session.scalar(
        select(EasyBooksRawRecord.id).where(
            EasyBooksRawRecord.source_system == "easybooks",
            EasyBooksRawRecord.entity_type == entity_type,
            EasyBooksRawRecord.source_id == source_id,
            EasyBooksRawRecord.payload_hash == digest,
        )
    )
    if exists:
        return False
    session.add(
        EasyBooksRawRecord(
            source_system="easybooks",
            entity_type=entity_type,
            source_id=source_id,
            payload=payload,
            payload_hash=digest,
            sync_run_id=run.id,
        )
    )
    return True


def _catalog_customer(session: Session, document: dict[str, Any]) -> None:
    code = document.get("accounting_object_code")
    name = document.get("accounting_object_name")
    if not code or not name:
        return
    customer = session.scalar(
        select(Customer).where(Customer.easybooks_accounting_object_code == code)
    )
    if customer is None:
        session.add(Customer(name=name, easybooks_accounting_object_code=code))
    elif customer.name != name:
        customer.name = name


def _catalog_product(session: Session, line: dict[str, Any]) -> None:
    source_id = line.get("material_goods_id")
    code = line.get("material_goods_code")
    name = line.get("material_goods_name")
    unit = line.get("unit")
    if not name or not unit or (not source_id and not code):
        return
    criteria = []
    if source_id:
        criteria.append(Product.easybooks_material_goods_id == source_id)
    if code:
        criteria.append(Product.code == code)
    product = session.scalar(select(Product).where(or_(*criteria)))
    if product is None:
        session.add(Product(code=code, name=name, unit=unit, easybooks_material_goods_id=source_id))
    else:
        product.name = name
        product.unit = unit
        if source_id and not product.easybooks_material_goods_id:
            product.easybooks_material_goods_id = source_id


def _replace_sales_lines(
    session: Session, document: SalesDocument, lines: list[dict[str, Any]]
) -> None:
    existing = {line.source_line_key: line for line in document.lines}
    seen = set()
    for values in lines:
        key = values["source_line_key"]
        seen.add(key)
        line = existing.get(key)
        if line is None:
            line = SalesLine(sales_document_id=document.id, **values)
            session.add(line)
        else:
            for name, value in values.items():
                setattr(line, name, value)
        _catalog_product(session, values)
    stale_ids = [line.id for key, line in existing.items() if key not in seen]
    if stale_ids:
        session.execute(delete(SalesLine).where(SalesLine.id.in_(stale_ids)))


def _replace_purchase_lines(
    session: Session, document: PurchaseDocument, lines: list[dict[str, Any]]
) -> None:
    existing = {line.source_line_key: line for line in document.lines}
    seen = set()
    for values in lines:
        key = values["source_line_key"]
        seen.add(key)
        line = existing.get(key)
        if line is None:
            line = PurchaseLine(purchase_document_id=document.id, **values)
            session.add(line)
        else:
            for name, value in values.items():
                setattr(line, name, value)
        # Purchase report has no observed stable material ID; code is the safe fallback.
        _catalog_product(
            session,
            {
                "material_goods_id": None,
                "material_goods_code": values.get("material_goods_code"),
                "material_goods_name": values.get("material_goods_name"),
                "unit": values.get("unit"),
            },
        )
    stale_ids = [line.id for key, line in existing.items() if key not in seen]
    if stale_ids:
        session.execute(delete(PurchaseLine).where(PurchaseLine.id.in_(stale_ids)))


def _upsert_sales(
    session: Session,
    run: EasyBooksSyncRun,
    source: dict[str, Any],
    raw_lines: list[dict[str, Any]],
) -> tuple[str, int]:
    normalized = normalize_sales_document(source)
    source_id = normalized["source_id"]
    lines = normalize_sales_lines(source_id, raw_lines)
    combined_hash = payload_hash({"document": normalized, "lines": lines})
    warnings = reconcile_sales(normalized, lines)
    _preserve_raw(session, run, "sales_document", source_id, source)
    _preserve_raw(session, run, "sales_lines", source_id, raw_lines)

    document = session.scalar(
        select(SalesDocument).where(
            SalesDocument.source_system == "easybooks", SalesDocument.source_id == source_id
        )
    )
    if document is None:
        values = {**normalized, "normalized_hash": combined_hash}
        document = SalesDocument(**values)
        session.add(document)
        session.flush()
        outcome = "created"
    elif document.normalized_hash == combined_hash:
        outcome = "unchanged"
    else:
        for name, value in normalized.items():
            setattr(document, name, value)
        document.normalized_hash = combined_hash
        document.synced_at = utc_now()
        outcome = "updated"
    if outcome != "unchanged":
        _replace_sales_lines(session, document, lines)
        _catalog_customer(session, normalized)
    for warning in warnings:
        logger.warning(
            warning,
            extra={"sync_run_id": run.id, "entity_type": "sales_document", "source_id": source_id},
        )
    return outcome, len(warnings)


def _upsert_purchase(
    session: Session,
    run: EasyBooksSyncRun,
    source_id: str,
    rows: list[dict[str, Any]],
) -> str:
    normalized = normalize_purchase_document(source_id, rows)
    lines = normalize_purchase_lines(source_id, rows)
    combined_hash = payload_hash({"document": normalized, "lines": lines})
    _preserve_raw(session, run, "purchase_document", source_id, rows)
    document = session.scalar(
        select(PurchaseDocument).where(
            PurchaseDocument.source_system == "easybooks",
            PurchaseDocument.source_id == source_id,
        )
    )
    if document is None:
        values = {**normalized, "normalized_hash": combined_hash}
        document = PurchaseDocument(**values)
        session.add(document)
        session.flush()
        outcome = "created"
    elif document.normalized_hash == combined_hash:
        outcome = "unchanged"
    else:
        for name, value in normalized.items():
            setattr(document, name, value)
        document.normalized_hash = combined_hash
        document.synced_at = utc_now()
        outcome = "updated"
    if outcome != "unchanged":
        _replace_purchase_lines(session, document, lines)
    return outcome


def sync_bundle(
    session: Session,
    bundle: FixtureBundle,
    *,
    mode: str = "fixture",
    from_date: date | None = None,
    to_date: date | None = None,
) -> EasyBooksSyncRun:
    run = EasyBooksSyncRun(mode=mode, from_date=from_date, to_date=to_date)
    session.add(run)
    session.commit()
    logger.info(
        "EasyBooks sync started",
        extra={"sync_run_id": run.id, "source": "easybooks", "mode": mode},
    )

    grouped_purchases = group_purchase_rows(bundle.purchase_rows)
    work: list[tuple[str, Any]] = [("sales", source) for source in bundle.sales_documents] + [
        ("purchase", (source_id, rows)) for source_id, rows in grouped_purchases.items()
    ]
    run.documents_seen = len(work)
    for entity_type, item in work:
        try:
            with session.begin_nested():
                if entity_type == "sales":
                    source_id = str(item.get("id", "missing"))
                    outcome, warning_count = _upsert_sales(
                        session, run, item, bundle.sales_lines.get(source_id, [])
                    )
                    run.reconciliation_warnings += warning_count
                else:
                    source_id, rows = item
                    outcome = _upsert_purchase(session, run, source_id, rows)
                if outcome == "created":
                    run.documents_created += 1
                elif outcome == "updated":
                    run.documents_updated += 1
                else:
                    run.documents_unchanged += 1
        except Exception as exc:  # each source document is independently auditable
            run.documents_failed += 1
            logger.exception(
                "EasyBooks document sync failed",
                extra={
                    "sync_run_id": run.id,
                    "entity_type": entity_type,
                    "source_id": source_id,
                },
            )
            run.error_summary = str(exc)[:2000]

    run.finished_at = utc_now()
    run.status = SyncStatus.PARTIAL if run.documents_failed else SyncStatus.SUCCEEDED
    session.commit()
    logger.info(
        "EasyBooks sync finished",
        extra={
            "sync_run_id": run.id,
            "source": "easybooks",
            "mode": mode,
            "documents_seen": run.documents_seen,
            "documents_failed": run.documents_failed,
        },
    )
    return run
