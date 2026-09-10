from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.integrations.easybooks.client import (
    EasyBooksAuthError,
    EasyBooksClient,
    EasyBooksConfigurationError,
)
from app.integrations.easybooks.contracts import (
    CatalogItem,
    PurchaseLineRecord,
    SalesDocumentRecord,
    SalesLineRecord,
)
from app.integrations.easybooks.normalization import (
    group_purchase_rows,
    normalize_purchase_document,
    normalize_purchase_lines,
    normalize_sales_document,
    normalize_sales_lines,
    payload_hash,
    purchase_catalog_item,
    report_total_rows,
    sales_catalog_item,
    sales_customer_code,
)
from app.integrations.easybooks.reconciliation import check_integrity, reconcile_sales
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

_SECRET_PATTERN = re.compile(
    r"(?:Bearer\s+[A-Za-z0-9_\-\.]+)|(?:[a-zA-Z0-9_\-]+(?:token|password|cookie|secret)=[^\s&]+)",
    re.IGNORECASE,
)


def _sanitize_error(msg: str) -> str:
    """Strip tokens, cookies, or secrets from error messages before storing."""
    return _SECRET_PATTERN.sub("[REDACTED]", msg)


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
    failed_line_document_ids: set[str] = field(default_factory=set)
    failed_line_reasons: dict[str, str] = field(default_factory=dict)

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
        failed_ids = set(payload.get("failed_line_document_ids", []))
        failed_reasons = dict(payload.get("failed_line_reasons", {}))
        return cls(
            documents,
            lines,
            purchases,
            failed_line_document_ids=failed_ids,
            failed_line_reasons=failed_reasons,
        )


# The sales list is an observed plain JSON array. These envelope keys exist only
# for the two endpoints whose response shape has not been directly observed: the
# purchase dynamic report and the sales detail read.
ROW_ENVELOPE_KEYS = ("data", "result", "results", "items", "content", "rows")


def _find_rows(response: Any) -> list[dict[str, Any]] | None:
    """Locate the row list in a response. An empty list is a valid answer."""
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
    """Read the document count returned by ``sa-invoice-count``.

    The observed contract is a bare non-negative JSON integer. A numeric string
    is accepted because that costs nothing; every other shape yields None rather
    than a guessed number.
    """
    if isinstance(response, bool):
        return None
    if isinstance(response, int):
        return response if response >= 0 else None
    if isinstance(response, str):
        text = response.strip()
        return int(text) if text.isdigit() else None
    return None


def fetch_sales_documents(
    client: EasyBooksClient, from_date: date, to_date: date
) -> tuple[list[dict[str, Any]], list[str]]:
    """Read the complete sales list for the window in one request.

    ``sa-invoice-objects-filter`` returns every matching document as a plain JSON
    array; EasyBooks paginates it client-side, so no paging request is made. The
    companion count read is a completeness check: disagreement is recorded as a
    reconciliation warning, and a count failure never aborts ingestion.
    """
    warnings: list[str] = []
    expected: int | None = None
    try:
        expected = _extract_count(client.sales_count(from_date, to_date))
    except Exception as exc:  # advisory read; ingestion continues without it
        warnings.append(f"sales count unavailable: {exc}")
    if expected is None and not warnings:
        warnings.append("sales count response was not a recognised number")

    documents = _extract_rows(client.sales_documents(from_date, to_date))
    if expected is not None and len(documents) != expected:
        warnings.append(
            f"sales count reported {expected} documents but {len(documents)} were retrieved"
        )
    return documents, warnings


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
    failed_line_document_ids: set[str] = set()
    failed_line_reasons: dict[str, str] = {}
    if include_lines:
        for document in documents:
            doc_id = str(document.get("id", ""))
            try:
                sales_lines[doc_id] = _extract_rows(client.sales_lines(doc_id))
            except (EasyBooksAuthError, EasyBooksConfigurationError):
                raise
            except Exception as exc:
                failed_line_document_ids.add(doc_id)
                clean_err = _sanitize_error(str(exc))
                failed_line_reasons[doc_id] = clean_err
                warnings.append(f"sales detail unavailable for document {doc_id}: {clean_err}")
    else:
        warnings.append("sales details were not retrieved; existing normalized lines are kept")
    try:
        purchase_rows = _extract_rows(client.purchase_report(from_date, to_date))
    except (EasyBooksAuthError, EasyBooksConfigurationError):
        raise
    except Exception as exc:
        # The purchase dynamic-report request body has never been directly observed
        # and the endpoint rejects the current one. A broken purchase read must not
        # discard a healthy sales read, so it degrades to a warning.
        clean_err = _sanitize_error(str(exc))
        warnings.append(f"purchase report unavailable: {clean_err}")
        purchase_rows = []
    return FixtureBundle(
        documents,
        sales_lines,
        purchase_rows,
        sales_lines_available=include_lines,
        warnings=warnings,
        failed_line_document_ids=failed_line_document_ids,
        failed_line_reasons=failed_line_reasons,
    )


def _record_raw(
    session: Session,
    run: EasyBooksSyncRun,
    entity_type: str,
    source_id: str,
    payload: dict[str, Any] | list[Any],
) -> EasyBooksRawRecord:
    """Return the raw version for this exact payload, storing it if it is new.

    The raw layer is append-only: an identical payload reuses the version already
    held, and a changed one is added beside it. Nothing here ever rewrites a
    stored payload, which is what lets a normalized row be reproduced from the
    bytes that produced it.
    """
    digest = payload_hash(payload)
    existing = session.scalar(
        select(EasyBooksRawRecord).where(
            EasyBooksRawRecord.source_system == "easybooks",
            EasyBooksRawRecord.entity_type == entity_type,
            EasyBooksRawRecord.source_id == source_id,
            EasyBooksRawRecord.payload_hash == digest,
        )
    )
    if existing is not None:
        return existing
    record = EasyBooksRawRecord(
        source_system="easybooks",
        entity_type=entity_type,
        source_id=source_id,
        payload=payload,
        payload_hash=digest,
        sync_run_id=run.id,
    )
    session.add(record)
    session.flush()
    return record


def _link_sales_lineage(
    document: SalesDocument,
    run: EasyBooksSyncRun,
    header_raw: EasyBooksRawRecord,
    lines_raw: EasyBooksRawRecord | None,
) -> None:
    """Point a normalized sales document at the raw versions behind it.

    Applied even when the normalized content is unchanged, because a source
    payload can change in a field UniOps does not normalize. The pointer must
    name the newest version that yields this content, not the first one that
    happened to.
    """
    lines_id = lines_raw.id if lines_raw is not None else document.source_lines_raw_record_id
    if (
        document.source_raw_record_id == header_raw.id
        and document.source_lines_raw_record_id == lines_id
    ):
        return
    document.source_raw_record_id = header_raw.id
    document.source_lines_raw_record_id = lines_id
    document.sync_run_id = run.id


def _link_purchase_lineage(
    document: PurchaseDocument, run: EasyBooksSyncRun, raw: EasyBooksRawRecord
) -> None:
    if document.source_raw_record_id == raw.id:
        return
    document.source_raw_record_id = raw.id
    document.sync_run_id = run.id


def _catalog_customer(session: Session, document: SalesDocumentRecord) -> None:
    code = document.accounting_object_code
    name = document.accounting_object_name
    if not code or not name:
        return
    customer = session.scalar(
        select(Customer).where(Customer.easybooks_accounting_object_code == code)
    )
    if customer is None:
        session.add(Customer(name=name, easybooks_accounting_object_code=code))
    elif customer.name != name:
        customer.name = name


def _catalog_product(session: Session, item: CatalogItem) -> None:
    source_id, code, name, unit = item.source_id, item.code, item.name, item.unit
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
    session: Session, document: SalesDocument, lines: list[SalesLineRecord]
) -> None:
    existing = {line.source_line_key: line for line in document.lines}
    seen = set()
    for record in lines:
        seen.add(record.source_line_key)
        line = existing.get(record.source_line_key)
        if line is None:
            session.add(SalesLine(sales_document_id=document.id, **record.as_columns()))
        else:
            for name, value in record.as_columns().items():
                setattr(line, name, value)
        _catalog_product(session, sales_catalog_item(record))
    stale_ids = [line.id for key, line in existing.items() if key not in seen]
    if stale_ids:
        session.execute(delete(SalesLine).where(SalesLine.id.in_(stale_ids)))


def _replace_purchase_lines(
    session: Session, document: PurchaseDocument, lines: list[PurchaseLineRecord]
) -> None:
    existing = {line.source_line_key: line for line in document.lines}
    seen = set()
    for record in lines:
        seen.add(record.source_line_key)
        line = existing.get(record.source_line_key)
        if line is None:
            session.add(PurchaseLine(purchase_document_id=document.id, **record.as_columns()))
        else:
            for name, value in record.as_columns().items():
                setattr(line, name, value)
        _catalog_product(session, purchase_catalog_item(record))
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
    record = normalize_sales_document(source)
    source_id = record.source_id
    lines = normalize_sales_lines(source_id, raw_lines) if lines_available else []
    warnings = reconcile_sales(record, lines) if lines_available else []
    # The header names the customer but does not code it, so take the code from the
    # lines. Without this the document has no canonical customer to link to. A
    # header-only read leaves it unset rather than guessing.
    if lines_available and not record.accounting_object_code:
        code, code_warnings = sales_customer_code(lines)
        if code:
            record = replace(record, accounting_object_code=code)
        warnings.extend(code_warnings)
    # A header-only read hashes a fixed marker instead of an empty line list, so
    # repeated header-only runs stay idempotent and never look like line deletion.
    line_fingerprint: Any = (
        [line.as_hash_payload() for line in lines] if lines_available else "not-retrieved"
    )
    combined_hash = payload_hash(
        {"document": record.as_hash_payload(), "lines": line_fingerprint}
    )
    header_raw = _record_raw(session, run, "sales_document", source_id, source)
    lines_raw = (
        _record_raw(session, run, "sales_lines", source_id, raw_lines) if lines_available else None
    )

    document = session.scalar(
        select(SalesDocument).where(
            SalesDocument.source_system == "easybooks", SalesDocument.source_id == source_id
        )
    )
    if document is None:
        document = SalesDocument(**record.as_columns(), normalized_hash=combined_hash)
        session.add(document)
        session.flush()
        outcome = "created"
    elif document.normalized_hash == combined_hash:
        outcome = "unchanged"
    else:
        for name, value in record.as_columns().items():
            setattr(document, name, value)
        document.normalized_hash = combined_hash
        document.synced_at = utc_now()
        outcome = "updated"
    _link_sales_lineage(document, run, header_raw, lines_raw)
    if outcome != "unchanged":
        if lines_available:
            _replace_sales_lines(session, document, lines)
        _catalog_customer(session, record)
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
    record = normalize_purchase_document(source_id, rows)
    lines = normalize_purchase_lines(source_id, rows)
    combined_hash = payload_hash(
        {
            "document": record.as_hash_payload(),
            "lines": [line.as_hash_payload() for line in lines],
        }
    )
    raw = _record_raw(session, run, "purchase_document", source_id, rows)
    document = session.scalar(
        select(PurchaseDocument).where(
            PurchaseDocument.source_system == "easybooks",
            PurchaseDocument.source_id == source_id,
        )
    )
    if document is None:
        document = PurchaseDocument(**record.as_columns(), normalized_hash=combined_hash)
        session.add(document)
        session.flush()
        outcome = "created"
    elif document.normalized_hash == combined_hash:
        outcome = "unchanged"
    else:
        for name, value in record.as_columns().items():
            setattr(document, name, value)
        document.normalized_hash = combined_hash
        document.synced_at = utc_now()
        outcome = "updated"
    _link_purchase_lineage(document, run, raw)
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
    run_id = run.id
    logger.info(
        "EasyBooks sync started",
        extra={"sync_run_id": run_id, "source": "easybooks", "mode": mode},
    )

    try:
        for warning in bundle.warnings:
            run.reconciliation_warnings += 1
            logger.warning(
                warning,
                extra={
                    "sync_run_id": run.id,
                    "source": "easybooks",
                    "entity_type": "sales_retrieval",
                },
            )

        # The purchase report's grand-total footer is not a document. Dropping it is
        # reported rather than silent, so a change in the report's shape is visible.
        skipped_totals = len(report_total_rows(bundle.purchase_rows))
        if skipped_totals:
            run.reconciliation_warnings += skipped_totals
            logger.warning(
                f"{skipped_totals} purchase report total rows were not ingested as documents",
                extra={
                    "sync_run_id": run.id,
                    "source": "easybooks",
                    "entity_type": "purchase_report",
                },
            )

        errors: list[str] = []
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
                        line_fetch_failed = source_id in bundle.failed_line_document_ids
                        lines_available = bundle.sales_lines_available and not line_fetch_failed
                        outcome, warning_count = _upsert_sales(
                            session,
                            run,
                            item,
                            bundle.sales_lines.get(source_id, []),
                            lines_available=lines_available,
                        )
                        run.reconciliation_warnings += warning_count
                        if line_fetch_failed:
                            run.documents_failed += 1
                            reason = (
                                bundle.failed_line_reasons.get(source_id)
                                or "sales detail unavailable"
                            )
                            errors.append(f"sales detail {source_id}: {_sanitize_error(reason)}")
                    else:
                        line_fetch_failed = False
                        source_id, rows = item
                        outcome = _upsert_purchase(session, run, source_id, rows)

                    if not line_fetch_failed:
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
                errors.append(f"{entity_type} {source_id}: {_sanitize_error(str(exc))}")

        # Validate/reconcile: what was just published must hold together, whatever
        # the source said. Breaks are reported, never silently accepted.
        for warning in check_integrity(session).warnings:
            run.reconciliation_warnings += 1
            logger.warning(
                warning,
                extra={"sync_run_id": run.id, "source": "easybooks", "entity_type": "integrity"},
            )

        if errors:
            run.error_summary = "; ".join(errors)[:2000]

        run.finished_at = utc_now()
        if run.documents_failed > 0 and (
            run.documents_created + run.documents_updated + run.documents_unchanged == 0
        ):
            run.status = SyncStatus.FAILED
        elif run.documents_failed > 0:
            run.status = SyncStatus.PARTIAL
        else:
            run.status = SyncStatus.SUCCEEDED
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

    except Exception as fatal_exc:
        session.rollback()
        failed_run = session.get(EasyBooksSyncRun, run_id)
        if failed_run is not None:
            failed_run.finished_at = utc_now()
            failed_run.status = SyncStatus.FAILED
            cleaned_err = _sanitize_error(str(fatal_exc))
            failed_run.error_summary = f"Fatal sync error: {cleaned_err}"[:2000]
            session.commit()
        raise
