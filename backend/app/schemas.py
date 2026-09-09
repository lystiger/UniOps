from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import OrderStatus, UserRole


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
