from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    catalog_create_access,
    catalog_read_access,
    read_access,
    write_access,
)
from app.database import get_db
from app.errors import ApiError
from app.models import ProductStatus
from app.schemas import (
    CustomerCreate,
    CustomerRead,
    CustomerReceivableDetailRead,
    ProductCreate,
    ProductRead,
    ProductUpdate,
)
from app.services import analytics, catalog

router = APIRouter(tags=["catalog"])


@router.get("/customers", response_model=list[CustomerRead], dependencies=[read_access])
async def list_customers(
    search: str | None = Query(default=None, max_length=100),
    session: Session = Depends(get_db),
):
    return catalog.list_customers(session, search)


@router.post(
    "/customers", response_model=CustomerRead, status_code=status.HTTP_201_CREATED,
    dependencies=[write_access],
)
async def create_customer(data: CustomerCreate, session: Session = Depends(get_db)):
    try:
        return catalog.create_customer(session, data)
    except catalog.CatalogConflict as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
            code=getattr(exc, "code", "CUSTOMER_CODE_EXISTS"),
            params=getattr(exc, "params", {}),
        ) from exc


@router.get(
    "/products", response_model=list[ProductRead], dependencies=[catalog_read_access]
)
async def list_products(
    search: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=100),
    product_status: ProductStatus | None = Query(default=None, alias="status"),
    session: Session = Depends(get_db),
):
    return catalog.list_products(
        session,
        search=search,
        category=category,
        status=product_status.value if product_status else None,
    )


def _product_not_found(exc: catalog.CatalogNotFound) -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(exc),
        code=exc.code,
        params=exc.params,
    )


@router.get(
    "/products/{product_id}", response_model=ProductRead, dependencies=[catalog_read_access]
)
async def get_product(product_id: str, session: Session = Depends(get_db)):
    try:
        return catalog.get_product(session, product_id)
    except catalog.CatalogNotFound as exc:
        raise _product_not_found(exc) from exc


@router.post(
    "/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED,
    dependencies=[catalog_create_access],
)
async def create_product(data: ProductCreate, session: Session = Depends(get_db)):
    try:
        return catalog.create_product(session, data)
    except catalog.CatalogConflict as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
            code=getattr(exc, "code", "PRODUCT_CODE_EXISTS"),
            params=getattr(exc, "params", {}),
        ) from exc


@router.patch(
    "/products/{product_id}", response_model=ProductRead, dependencies=[write_access]
)
async def update_product(
    product_id: str, data: ProductUpdate, session: Session = Depends(get_db)
):
    """Change a canonical product's descriptive fields or discontinue it.

    Signed-in office staff only: the catalogue service key cannot change a
    canonical product. The SKU is not accepted here and never changes.
    """
    try:
        return catalog.update_product(session, product_id, data)
    except catalog.CatalogNotFound as exc:
        raise _product_not_found(exc) from exc


@router.get(
    "/customers/{customer_id}/receivables",
    response_model=CustomerReceivableDetailRead,
    dependencies=[read_access],
)
async def customer_receivables(
    customer_id: str,
    as_of: date | None = Query(default=None),
    session: Session = Depends(get_db),
):
    """One customer's invoices and the UniOps orders linked to them."""
    try:
        return analytics.customer_receivable(session, customer_id, as_of)
    except analytics.CustomerNotFound as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
            code=getattr(exc, "code", "CUSTOMER_NOT_FOUND"),
            params=getattr(exc, "params", {}),
        ) from exc
