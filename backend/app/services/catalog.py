import re
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Customer, Product, ProductSkuSequence
from app.schemas import CustomerCreate, ProductCreate, ProductUpdate

# The SKU is a non-semantic sequence number: it says nothing about ply, size or
# packaging, so no change to those can ever make it wrong.
SKU_PREFIX = "UG"
SKU_PATTERN = re.compile(r"^UG\d{6}$")
SKU_MAX_NUMBER = 999_999


class CatalogConflict(ValueError):
    def __init__(
        self,
        message: str,
        code: str = "CATALOG_CONFLICT",
        params: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.params = params or {}


class CatalogNotFound(ValueError):
    def __init__(
        self,
        message: str,
        code: str = "CATALOG_NOT_FOUND",
        params: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.params = params or {}


def create_customer(session: Session, data: CustomerCreate) -> Customer:
    customer = Customer(**data.model_dump())
    session.add(customer)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise CatalogConflict(
            "customer source code or source ID already exists",
            code="CUSTOMER_CODE_EXISTS",
        ) from exc
    session.refresh(customer)
    return customer


def list_customers(session: Session, search: str | None = None) -> list[Customer]:
    statement = select(Customer).order_by(Customer.name)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Customer.name.ilike(pattern),
                Customer.tax_code.ilike(pattern),
                Customer.easybooks_accounting_object_code.ilike(pattern),
            )
        )
    return list(session.scalars(statement))


def allocate_sku(session: Session) -> str:
    """Take the next SKU from the sequence inside the caller's transaction.

    The increment is a single UPDATE, so on PostgreSQL it holds the sequence
    row lock until the caller commits or rolls back: two concurrent creations
    queue behind each other and cannot read the same number. A rolled-back
    creation gives its number back; a committed one is never handed out again.
    """
    number = session.execute(
        update(ProductSkuSequence)
        .where(ProductSkuSequence.id == 1)
        .values(last_number=ProductSkuSequence.last_number + 1)
        .returning(ProductSkuSequence.last_number)
    ).scalar_one_or_none()
    if number is None:
        raise RuntimeError(
            "product_sku_sequence has no row; run the database migrations before creating products"
        )
    if number > SKU_MAX_NUMBER:
        raise CatalogConflict(
            "the SKU sequence is exhausted", code="SKU_SEQUENCE_EXHAUSTED"
        )
    return f"{SKU_PREFIX}{number:06d}"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def create_product(session: Session, data: ProductCreate) -> Product:
    product = Product(
        sku=allocate_sku(session),
        name=data.name.strip(),
        unit=data.unit.strip(),
        category=data.category.strip(),
        status=data.status.value,
        specifications=data.specifications,
        code=_clean(data.code),
        easybooks_material_goods_id=_clean(data.easybooks_material_goods_id),
    )
    session.add(product)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise CatalogConflict(
            "product code or EasyBooks material ID already exists",
            code="PRODUCT_CODE_EXISTS",
        ) from exc
    return product


def update_product(session: Session, product_id: str, data: ProductUpdate) -> Product:
    product = get_product(session, product_id)
    for field in ("name", "unit", "category"):
        value = getattr(data, field)
        if value is not None:
            setattr(product, field, value.strip())
    if data.status is not None:
        product.status = data.status.value
    if data.specifications is not None:
        product.specifications = data.specifications
    session.commit()
    return product


def get_product(session: Session, product_id: str) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise CatalogNotFound(f"product '{product_id}' not found", code="PRODUCT_NOT_FOUND")
    return product


def list_products(
    session: Session,
    search: str | None = None,
    category: str | None = None,
    status: str | None = None,
) -> list[Product]:
    statement = select(Product).order_by(Product.sku)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
                Product.code.ilike(pattern),
            )
        )
    if category:
        statement = statement.where(Product.category == category)
    if status:
        statement = statement.where(Product.status == status)
    return list(session.scalars(statement))
