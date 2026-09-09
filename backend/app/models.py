from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class OrderStatus(StrEnum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    SCHEDULED = "SCHEDULED"
    IN_PRODUCTION = "IN_PRODUCTION"
    READY = "READY"
    DELIVERY_PENDING = "DELIVERY_PENDING"
    DELIVERED = "DELIVERED"
    INVOICED = "INVOICED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    OFFICE = "OFFICE"
    FACTORY_READ = "FACTORY_READ"


class SyncStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_user_username"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False, length=20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    """A signed-in browser.

    Only the SHA-256 of the cookie value is stored, so a database copy cannot be
    replayed as a live session the way a stored raw token could.
    """

    __tablename__ = "user_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_user_session_token"),
        Index("ix_user_sessions_user", "user_id"),
        Index("ix_user_sessions_expires", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("easybooks_accounting_object_code", name="uq_customer_eb_code"),
        UniqueConstraint("easybooks_source_id", name="uq_customer_eb_source_id"),
        Index("ix_customers_name", "name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255))
    tax_code: Mapped[str | None] = mapped_column(String(50))
    easybooks_accounting_object_code: Mapped[str | None] = mapped_column(String(100))
    easybooks_source_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    orders: Mapped[list[Order]] = relationship(back_populates="customer")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("code", name="uq_product_code"),
        UniqueConstraint("easybooks_material_goods_id", name="uq_product_eb_material_id"),
        Index("ix_products_name", "name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(50))
    easybooks_material_goods_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("order_number", name="uq_order_number"),
        Index("ix_orders_status_required", "status", "required_date"),
        Index("ix_orders_customer", "customer_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    order_number: Mapped[str] = mapped_column(String(32))
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"))
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=32), default=OrderStatus.DRAFT
    )
    order_date: Mapped[date] = mapped_column(Date)
    required_date: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    customer: Mapped[Customer] = relationship(back_populates="orders")
    lines: Mapped[list[OrderLine]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderLine.position"
    )


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = (
        UniqueConstraint("order_id", "position", name="uq_order_line_position"),
        Index("ix_order_lines_order", "order_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=True
    )
    position: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit: Mapped[str] = mapped_column(String(50))
    agreed_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    order: Mapped[Order] = relationship(back_populates="lines")
    product: Mapped[Product | None] = relationship()


class EasyBooksSyncRun(Base):
    __tablename__ = "easybooks_sync_runs"
    __table_args__ = (Index("ix_sync_runs_started", "started_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source: Mapped[str] = mapped_column(String(32), default="easybooks")
    mode: Mapped[str] = mapped_column(String(20))
    from_date: Mapped[date | None] = mapped_column(Date)
    to_date: Mapped[date | None] = mapped_column(Date)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, native_enum=False, length=20), default=SyncStatus.RUNNING
    )
    documents_seen: Mapped[int] = mapped_column(Integer, default=0)
    documents_created: Mapped[int] = mapped_column(Integer, default=0)
    documents_updated: Mapped[int] = mapped_column(Integer, default=0)
    documents_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    documents_failed: Mapped[int] = mapped_column(Integer, default=0)
    reconciliation_warnings: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)


class EasyBooksRawRecord(Base):
    __tablename__ = "easybooks_raw_records"
    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "entity_type",
            "source_id",
            "payload_hash",
            name="uq_raw_source_payload",
        ),
        Index("ix_raw_lookup", "source_system", "entity_type", "source_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_system: Mapped[str] = mapped_column(String(32), default="easybooks")
    entity_type: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(255))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    payload: Mapped[dict[str, Any] | list[Any]] = mapped_column(JSON)
    payload_hash: Mapped[str] = mapped_column(String(64))
    sync_run_id: Mapped[str] = mapped_column(
        ForeignKey("easybooks_sync_runs.id", ondelete="RESTRICT")
    )


class SalesDocument(Base):
    __tablename__ = "sales_documents"
    __table_args__ = (
        UniqueConstraint("source_system", "source_id", name="uq_sales_source"),
        Index("ix_sales_document_date", "document_date"),
        Index("ix_sales_customer_code", "accounting_object_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_system: Mapped[str] = mapped_column(String(32), default="easybooks")
    source_id: Mapped[str] = mapped_column(String(100))
    source_type: Mapped[str | None] = mapped_column(String(100))
    source_document_number: Mapped[str | None] = mapped_column(String(100))
    company_id: Mapped[str | None] = mapped_column(String(100))
    document_date: Mapped[date | None] = mapped_column(Date)
    posted_date: Mapped[date | None] = mapped_column(Date)
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_series: Mapped[str | None] = mapped_column(String(100))
    accounting_object_code: Mapped[str | None] = mapped_column(String(100))
    accounting_object_name: Mapped[str | None] = mapped_column(String(255))
    currency_id: Mapped[str | None] = mapped_column(String(20))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    recorded: Mapped[bool | None] = mapped_column(Boolean)
    normalized_hash: Mapped[str] = mapped_column(String(64))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    lines: Mapped[list[SalesLine]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class SalesLine(Base):
    __tablename__ = "sales_lines"
    __table_args__ = (
        UniqueConstraint("sales_document_id", "source_line_key", name="uq_sales_line_source"),
        Index("ix_sales_lines_document", "sales_document_id"),
        Index("ix_sales_lines_product_code", "material_goods_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sales_document_id: Mapped[str] = mapped_column(
        ForeignKey("sales_documents.id", ondelete="CASCADE")
    )
    source_line_key: Mapped[str] = mapped_column(String(64))
    source_line_id: Mapped[str | None] = mapped_column(String(100))
    material_goods_id: Mapped[str | None] = mapped_column(String(100))
    material_goods_code: Mapped[str | None] = mapped_column(String(100))
    material_goods_name: Mapped[str | None] = mapped_column(String(255))
    repository_code: Mapped[str | None] = mapped_column(String(100))
    accounting_object_code: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str | None] = mapped_column(String(50))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    document: Mapped[SalesDocument] = relationship(back_populates="lines")


class PurchaseDocument(Base):
    __tablename__ = "purchase_documents"
    __table_args__ = (
        UniqueConstraint("source_system", "source_id", name="uq_purchase_source"),
        Index("ix_purchase_document_date", "document_date"),
        Index("ix_purchase_vendor_code", "vendor_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_system: Mapped[str] = mapped_column(String(32), default="easybooks")
    source_id: Mapped[str] = mapped_column(String(100))
    source_type: Mapped[str | None] = mapped_column(String(100))
    source_document_number: Mapped[str | None] = mapped_column(String(100))
    document_date: Mapped[date | None] = mapped_column(Date)
    posted_date: Mapped[date | None] = mapped_column(Date)
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    vendor_code: Mapped[str | None] = mapped_column(String(100))
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    tax_code: Mapped[str | None] = mapped_column(String(50))
    currency_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("1"))
    total_purchase_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    normalized_hash: Mapped[str] = mapped_column(String(64))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    lines: Mapped[list[PurchaseLine]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class PurchaseLine(Base):
    __tablename__ = "purchase_lines"
    __table_args__ = (
        UniqueConstraint("purchase_document_id", "source_line_key", name="uq_purchase_line_source"),
        Index("ix_purchase_lines_document", "purchase_document_id"),
        Index("ix_purchase_lines_product_code", "material_goods_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    purchase_document_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_documents.id", ondelete="CASCADE")
    )
    source_line_key: Mapped[str] = mapped_column(String(64))
    material_goods_code: Mapped[str | None] = mapped_column(String(100))
    material_goods_name: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(50))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    purchase_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    # `thueGTGT` on the EasyBooks purchase report is the VAT amount in dong, not
    # a percentage. It was modelled as a rate and stored as NUMERIC(8,4), which
    # SQLite accepted silently and PostgreSQL rejects as a field overflow.
    vat_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    warehouse_code: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    document: Mapped[PurchaseDocument] = relationship(back_populates="lines")
