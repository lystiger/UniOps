import re
import threading
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Customer, Product, ProductSkuSequence
from app.schemas import CustomerCreate, ProductCreate

SKU_PATTERN = re.compile(r"^UG\d{6}$")
_sku_lock = threading.Lock()


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


def _get_highest_sku_number(session: Session) -> int:
    max_num = 0
    skus = session.scalars(select(Product.sku)).all()
    for s in skus:
        if s and s.startswith("UG") and s[2:].isdigit():
            max_num = max(max_num, int(s[2:]))
    return max_num


def generate_next_sku(session: Session) -> str:
    """Generate the next sequential non-semantic SKU (UG000001 form).

    Safe under concurrent creation using sequence row lock and atomic increment.
    """
    with _sku_lock:
        stmt = (
            update(ProductSkuSequence)
            .where(ProductSkuSequence.id == 1)
            .values(last_number=ProductSkuSequence.last_number + 1)
            .returning(ProductSkuSequence.last_number)
        )
        val = session.execute(stmt).scalar_one_or_none()
        if val is None:
            max_num = _get_highest_sku_number(session)
            seq = ProductSkuSequence(id=1, last_number=max_num + 1)
            session.add(seq)
            session.flush()
            val = seq.last_number
        else:
            session.flush()
        return f"UG{val:06d}"


def create_product(session: Session, data: ProductCreate) -> Product:
    sku = data.sku.strip() if data.sku else None
    if sku:
        if not SKU_PATTERN.match(sku):
            raise CatalogConflict(
                f"SKU '{sku}' must match the UG000001 non-semantic format",
                code="INVALID_SKU_FORMAT",
            )
        # Advance sequence if explicit SKU number is greater than current last_number
        sku_num = int(sku[2:])
        seq = session.scalar(
            select(ProductSkuSequence).where(ProductSkuSequence.id == 1).with_for_update()
        )
        if seq is None:
            highest = _get_highest_sku_number(session)
            seq = ProductSkuSequence(id=1, last_number=max(sku_num, highest))
            session.add(seq)
        elif sku_num > seq.last_number:
            seq.last_number = sku_num
        session.flush()
    else:
        sku = generate_next_sku(session)

    code = data.code or data.easybooks_code
    product = Product(
        sku=sku,
        name=data.name.strip(),
        unit=data.unit.strip(),
        category=data.category.strip() if data.category else "general",
        status=data.status if data.status else "active",
        specifications=data.specifications or {},
        code=code.strip() if code else None,
        easybooks_material_goods_id=data.easybooks_material_goods_id,
    )
    session.add(product)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        orig_msg = str(getattr(exc, "orig", exc)).lower()
        if "products.sku" in orig_msg or "uq_product_sku" in orig_msg or "key (sku)" in orig_msg:
            raise CatalogConflict(
                f"product SKU '{sku}' already exists",
                code="PRODUCT_SKU_EXISTS",
            ) from exc
        raise CatalogConflict(
            "product code or EasyBooks material ID already exists",
            code="PRODUCT_CODE_EXISTS",
        ) from exc
    session.refresh(product)
    return product


def get_product(session: Session, product_id: str) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise CatalogNotFound(f"product '{product_id}' not found", code="PRODUCT_NOT_FOUND")
    return product


def get_product_by_sku(session: Session, sku: str) -> Product:
    product = session.scalar(select(Product).where(Product.sku == sku))
    if product is None:
        raise CatalogNotFound(f"product with SKU '{sku}' not found", code="PRODUCT_NOT_FOUND")
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
