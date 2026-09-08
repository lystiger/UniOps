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
    # False when sales details were deliberately not retrieved (headers-only live
    # read). Existing normalized lines are then preserved untouched.
    sales_lines_available: bool = True
    # Retrieval-time findings, such as a sales count that disagrees with the
    # number of listed documents. Counted as sync-run reconciliation warnings.
    warnings: list[str] = field(default_factory=list)

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


ROW_ENVELOPE_KEYS = ("data", "result", "results", "items", "content", "rows", "pageData")
COUNT_ENVELOPE_KEYS = ("count", "total", "totalCount", "totalRow", "totalRows", "totalResult")


def _find_rows(response: Any) -> list[dict[str, Any]] | None:
    """Locate the row list in a response envelope. An empty list is a valid answer."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        for key in ROW_ENVELOPE_KEYS:
            if key not in response:
                continue
            nested = _find_rows(response[key])
            if nested is not None:
                return nested
    return None


def _extract_rows(response: Any) -> list[dict[str, Any]]:
    rows = _find_rows(response)
    if rows is None:
        raise ValueError("EasyBooks response did not contain a row list")
    return rows


def _extract_count(response: Any) -> int | None:
    """Read a document count from the companion count endpoint.

    The response envelope has not been verified against a live account, so every
    unrecognised shape yields None rather than a guessed number.
    """
    if isinstance(response, bool):
        return None
    if isinstance(response, int):
        return response if response >= 0 else None
    if isinstance(response, str):
        text = response.strip()
        return int(text) if text.isdigit() else None
    if isinstance(response, dict):
        for key in (*COUNT_ENVELOPE_KEYS, "data", "result", "value"):
            if key not in response:
                continue
            nested = _extract_count(response[key])
            if nested is not None:
                return nested
    if isinstance(response, list) and len(response) == 1:
        return _extract_count(response[0])
    return None


def _document_key(row: dict[str, Any]) -> str:
    """Stable per-page dedupe key; falls back to the payload when id is absent."""
    source_id = row.get("id")
    if source_id in (None, ""):
        return f"payload:{payload_hash(row)}"
    return str(source_id)


def fetch_sales_documents(
    client: EasyBooksClient, from_date: date, to_date: date
) -> tuple[list[dict[str, Any]], list[str]]:
    """Read the sales list, paging only when the operator configured paging.

    The companion count endpoint is advisory: it bounds the paging loop and
    reports disagreement, but a count failure never aborts ingestion.
    """
    warnings: list[str] = []
    expected: int | None = None
    try:
        expected = _extract_count(client.sales_count(from_date, to_date))
    except Exception as exc:  # advisory read; ingestion continues without it
        warnings.append(f"sales count unavailable: {exc}")
    if expected is None and not warnings:
        warnings.append("sales count response was not a recognised number")

    if not client.paging_enabled():
        documents = _extract_rows(client.sales_documents(from_date, to_date))
        warnings.extend(_count_warnings(len(documents), expected, paged=False))
        return documents, warnings

    page_size = client.sales_page_size
    if page_size is None:  # unreachable via paging_enabled; guarded explicitly
        raise ValueError("sales paging enabled without a page size")
    max_pages = client.settings.easybooks_sales_max_pages
    documents: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page_index in range(max_pages):
        rows = _extract_rows(client.sales_documents(from_date, to_date, page_index=page_index))
        if not rows:
            break
        fresh = [row for row in rows if _document_key(row) not in seen]
        if not fresh:
            # The page repeated documents already collected. Continuing would loop
            # forever against an endpoint that ignores the paging parameters.
            warnings.append(
                f"sales page {page_index} returned only already-seen documents; paging stopped"
            )
            break
        seen.update(_document_key(row) for row in fresh)
        documents.extend(fresh)
        if len(rows) < page_size:
            break
        if expected is not None and len(documents) >= expected:
            break
    else:
        warnings.append(
            f"sales paging stopped at the {max_pages}-page cap; the window may be incomplete"
        )

    warnings.extend(_count_warnings(len(documents), expected, paged=True))
    return documents, warnings


def _count_warnings(retrieved: int, expected: int | None, *, paged: bool) -> list[str]:
    if expected is None or retrieved == expected:
        return []
    detail = f"sales count reported {expected} documents but {retrieved} were retrieved"
    if not paged and retrieved < expected:
        detail += "; the sales list is likely paginated and paging is not configured"
    return [detail]


def fetch_live_bundle(
    client: EasyBooksClient,
    from_date: date,
    to_date: date,
    *,
    include_lines: bool = True,
) -> FixtureBundle:
    """Read known endpoints only; no endpoint discovery or write calls.

    ``include_lines=False`` retrieves sales headers and purchases without touching
    the sales-detail route, so list/count behaviour can be validated against a live
    account before the observed detail path is known.
    """
    documents, warnings = fetch_sales_documents(client, from_date, to_date)
    sales_lines: dict[str, list[dict[str, Any]]] = {}
    if include_lines:
        sales_lines = {
            str(document["id"]): _extract_rows(client.sales_lines(str(document["id"])))
            for document in documents
        }
    else:
        warnings.append("sales details were not retrieved; existing normalized lines are kept")
    purchase_rows = _extract_rows(client.purchase_report(from_date, to_date))
    return FixtureBundle(
        documents,
        sales_lines,
        purchase_rows,
        sales_lines_available=include_lines,
        warnings=warnings,
    )


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
    *,
    lines_available: bool = True,
) -> tuple[str, int]:
    normalized = normalize_sales_document(source)
    source_id = normalized["source_id"]
    lines = normalize_sales_lines(source_id, raw_lines) if lines_available else []
    # A header-only read hashes a fixed marker instead of an empty line list, so
    # repeated header-only runs stay idempotent and never look like line deletion.
    line_fingerprint: Any = lines if lines_available else "not-retrieved"
    combined_hash = payload_hash({"document": normalized, "lines": line_fingerprint})
    warnings = reconcile_sales(normalized, lines) if lines_available else []
    _preserve_raw(session, run, "sales_document", source_id, source)
    if lines_available:
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
        if lines_available:
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

    for warning in bundle.warnings:
        run.reconciliation_warnings += 1
        logger.warning(
            warning,
            extra={"sync_run_id": run.id, "source": "easybooks", "entity_type": "sales_retrieval"},
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
                        session,
                        run,
                        item,
                        bundle.sales_lines.get(source_id, []),
                        lines_available=bundle.sales_lines_available,
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
