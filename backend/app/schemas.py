from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import OrderStatus


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
