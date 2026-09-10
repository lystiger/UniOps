from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import LinkMethod, OrderStatus, UserRole
from app.services.exceptions_view import ExceptionCategory
from app.services.order_to_cash import AccountingStatus, DueStatus, PaymentStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CustomerCreate(ApiModel):
    name: str = Field(min_length=1, max_length=255)
    tax_code: str | None = Field(default=None, max_length=50)
    easybooks_accounting_object_code: str | None = Field(default=None, max_length=100)
    easybooks_source_id: str | None = Field(default=None, max_length=100)


class CustomerRead(CustomerCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class ProductCreate(ApiModel):
    code: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    unit: str = Field(min_length=1, max_length=50)
    easybooks_material_goods_id: str | None = Field(default=None, max_length=100)


class ProductRead(ProductCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class OrderLineInput(ApiModel):
    product_id: str | None = None
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    unit: str = Field(min_length=1, max_length=50)
    agreed_unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    notes: str | None = None

    @field_validator("quantity", "agreed_unit_price", mode="before")
    @classmethod
    def reject_binary_floats(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("decimal values must be sent as JSON strings or integers, not floats")
        return value


class OrderLineCreate(OrderLineInput):
    position: int | None = Field(default=None, ge=1)


class OrderLineUpdate(ApiModel):
    product_id: str | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=4)
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    agreed_unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    notes: str | None = None
    position: int | None = Field(default=None, ge=1)

    @field_validator("quantity", "agreed_unit_price", mode="before")
    @classmethod
    def reject_binary_floats(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("decimal values must be sent as JSON strings or integers, not floats")
        return value


class OrderCreate(ApiModel):
    customer_id: str
    order_date: date
    required_date: date
    notes: str | None = None
    lines: list[OrderLineCreate] = Field(min_length=1)


class OrderUpdate(ApiModel):
    customer_id: str | None = None
    order_date: date | None = None
    required_date: date | None = None
    notes: str | None = None


class OrderStatusChange(ApiModel):
    status: OrderStatus


class OrderLineRead(OrderLineInput):
    id: str
    order_id: str
    position: int
    product: ProductRead | None
    created_at: datetime
    updated_at: datetime


class OrderRead(ApiModel):
    id: str
    order_number: str
    customer_id: str
    customer: CustomerRead
    status: OrderStatus
    order_date: date
    required_date: date
    notes: str | None
    lines: list[OrderLineRead]
    created_at: datetime
    updated_at: datetime
    # Derived, never stored. Absent on a single-order read that did not ask for it.
    accounting_status: str | None = None


class OrderList(ApiModel):
    items: list[OrderRead]
    total: int


class SyncRunRead(ApiModel):
    id: str
    mode: str
    from_date: date | None
    to_date: date | None
    started_at: datetime
    finished_at: datetime | None
    status: str
    documents_seen: int
    documents_created: int
    documents_updated: int
    documents_unchanged: int
    documents_failed: int
    reconciliation_warnings: int
    error_summary: str | None


class LoginRequest(ApiModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class PasswordChange(ApiModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class UserRead(ApiModel):
    id: str
    username: str
    full_name: str | None
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class MonthlyAmountRead(ApiModel):
    month: str
    amount: Decimal
    document_count: int


class SalesSummaryRead(ApiModel):
    document_count: int
    customer_count: int
    total: Decimal
    vat_amount: Decimal
    # Documents EasyBooks gave no date. They cannot be placed in the window or in
    # a month, so they are reported here rather than folded silently into a total.
    undated_document_count: int
    by_month: list[MonthlyAmountRead]


class PurchaseSummaryRead(ApiModel):
    document_count: int
    supplier_count: int
    total: Decimal
    vat_amount: Decimal
    undated_document_count: int
    by_month: list[MonthlyAmountRead]


class CommercialOverviewRead(ApiModel):
    from_date: date | None
    to_date: date | None
    sales: SalesSummaryRead
    purchases: PurchaseSummaryRead
    # Gross commercial flow. Deliberately not called profit: purchases in a period
    # are not the cost of the goods sold in that period.
    sales_minus_purchases: Decimal


class InvoiceCandidateRead(ApiModel):
    sales_document_id: str
    source_id: str
    invoice_number: str | None
    invoice_series: str | None
    document_date: date | None
    subtotal: Decimal
    total_amount: Decimal
    confidence: Decimal
    evidence: dict[str, Any]


class LinkedInvoiceRead(ApiModel):
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
    # UNKNOWN until a payment source is observed. Never inferred from the invoice.
    payment_status: PaymentStatus
    due_date: date | None
    due_status: DueStatus


class OrderAccountingRead(ApiModel):
    order_id: str
    order_number: str
    # The production lifecycle and the accounting state are separate machines and
    # are reported separately. Neither is derived from the other.
    lifecycle_status: str
    order_total: Decimal | None
    accounting_status: AccountingStatus
    payment_status: PaymentStatus
    outstanding_amount: Decimal | None
    outstanding_status: str
    invoices: list[LinkedInvoiceRead]
    candidate_count: int


class InvoiceLinkCreate(ApiModel):
    sales_document_id: str = Field(min_length=1, max_length=36)


class CustomerReceivableRead(ApiModel):
    customer_id: str | None
    customer_code: str
    customer_name: str | None
    invoice_count: int
    total_invoiced: Decimal
    oldest_invoice_date: date | None
    newest_invoice_date: date | None
    # Null, not zero: zero would assert the customer owes nothing.
    outstanding_amount: Decimal | None
    overdue_amount: Decimal | None


class ReceivablesRead(ApiModel):
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
    # Says in words why the figures above are null, so a null is never read as
    # "nothing outstanding".
    outstanding_status: str
    due_status: str
    customers: list[CustomerReceivableRead]


class CustomerInvoiceRead(ApiModel):
    sales_document_id: str
    invoice_number: str | None
    invoice_series: str | None
    document_date: date | None
    total_amount: Decimal
    vat_amount: Decimal
    paid_amount: Decimal | None
    outstanding_amount: Decimal | None
    payment_status: PaymentStatus
    due_date: date | None
    due_status: DueStatus
    linked_order_numbers: list[str]


class CustomerReceivableDetailRead(ApiModel):
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
    invoices: list[CustomerInvoiceRead]


class ExceptionItemRead(ApiModel):
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


class ExceptionGroupRead(ApiModel):
    category: ExceptionCategory
    count: int
    items: list[ExceptionItemRead]


class ExceptionReportRead(ApiModel):
    as_of: date
    total: int
    groups: list[ExceptionGroupRead]
