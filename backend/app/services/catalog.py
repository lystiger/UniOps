from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Customer, Product
from app.schemas import CustomerCreate, ProductCreate


class CatalogConflict(ValueError):
    pass


def create_customer(session: Session, data: CustomerCreate) -> Customer:
    customer = Customer(**data.model_dump())
    session.add(customer)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise CatalogConflict("customer source code or source ID already exists") from exc
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


def create_product(session: Session, data: ProductCreate) -> Product:
    product = Product(**data.model_dump())
    session.add(product)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise CatalogConflict("product code or EasyBooks material ID already exists") from exc
    session.refresh(product)
    return product


def list_products(session: Session, search: str | None = None) -> list[Product]:
    statement = select(Product).order_by(Product.name)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(Product.name.ilike(pattern), Product.code.ilike(pattern)))
    return list(session.scalars(statement))
