from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import read_access, write_access
from app.database import get_db
from app.schemas import CustomerCreate, CustomerRead, ProductCreate, ProductRead
from app.services import catalog

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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/products", response_model=list[ProductRead], dependencies=[read_access])
async def list_products(
    search: str | None = Query(default=None, max_length=100),
    session: Session = Depends(get_db),
):
    return catalog.list_products(session, search)


@router.post(
    "/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED,
    dependencies=[write_access],
)
async def create_product(data: ProductCreate, session: Session = Depends(get_db)):
    try:
        return catalog.create_product(session, data)
    except catalog.CatalogConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
