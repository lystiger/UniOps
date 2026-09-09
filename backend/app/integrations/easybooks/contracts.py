"""Internal data contracts between the EasyBooks connector and the rest of UniOps.

These records are the boundary. Above them live EasyBooks field names
(``thueGTGT``, ``totalAllAmount``, ``giaTriMua``); below them only UniOps domain
names. Normalization is the single place where one is turned into the other, so
no application, service, or API code has to know what EasyBooks calls anything.

Each record is frozen. A normalized document is a statement about one observed
source payload, and rewriting it in place would make it a statement about
something else; the one derived value the sync layer adds (a sales customer code
taken from the lines) is applied with :func:`dataclasses.replace`.

``as_columns`` gives the model keyword arguments, ``as_hash_payload`` gives the
representation that change detection hashes. They differ for documents only:
``normalized_hash`` is part of the hashed representation but not a column the
normalizer owns, because the sync layer stores a combined document-plus-lines
hash there instead.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class SalesDocumentRecord:
    source_system: str
    source_id: str
    source_type: str | None
    source_document_number: str | None
    company_id: str | None
    document_date: date | None
    posted_date: date | None
    invoice_number: str | None
    invoice_series: str | None
    accounting_object_code: str | None
    accounting_object_name: str | None
    currency_id: str | None
    subtotal: Decimal
    discount_amount: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    recorded: bool | None
    normalized_hash: str

    def as_columns(self) -> dict[str, Any]:
        values = asdict(self)
        values.pop("normalized_hash")
        return values

    def as_hash_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SalesLineRecord:
    source_line_key: str
    source_line_id: str | None
    material_goods_id: str | None
    material_goods_code: str | None
    material_goods_name: str | None
    repository_code: str | None
    accounting_object_code: str | None
    unit: str | None
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    discount_amount: Decimal
    vat_amount: Decimal

    def as_columns(self) -> dict[str, Any]:
        return asdict(self)

    def as_hash_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PurchaseDocumentRecord:
    source_system: str
    source_id: str
    source_type: str | None
    source_document_number: str | None
    document_date: date | None
    posted_date: date | None
    invoice_number: str | None
    vendor_code: str | None
    vendor_name: str | None
    tax_code: str | None
    currency_rate: Decimal
    total_purchase_amount: Decimal
    normalized_hash: str

    def as_columns(self) -> dict[str, Any]:
        values = asdict(self)
        values.pop("normalized_hash")
        return values

    def as_hash_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PurchaseLineRecord:
    source_line_key: str
    material_goods_code: str | None
    material_goods_name: str | None
    unit: str | None
    quantity: Decimal
    unit_price: Decimal
    purchase_amount: Decimal
    discount_amount: Decimal
    # EasyBooks `thueGTGT`: VAT in dong, not a percentage. Absent on rows the
    # report leaves blank, which is why it is nullable rather than zero.
    vat_amount: Decimal | None
    warehouse_code: str | None
    description: str | None

    def as_columns(self) -> dict[str, Any]:
        return asdict(self)

    def as_hash_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CatalogItem:
    """What a normalized line says about a product, in UniOps terms."""

    source_id: str | None
    code: str | None
    name: str | None
    unit: str | None
