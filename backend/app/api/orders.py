from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OrderStatus
from app.schemas import (
    OrderCreate,
    OrderLineCreate,
    OrderLineUpdate,
    OrderList,
    OrderRead,
    OrderStatusChange,
    OrderUpdate,
)
from app.services import orders

router = APIRouter(prefix="/orders", tags=["orders"])


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, orders.OrderNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))


@router.get("", response_model=OrderList)
async def list_orders(
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=100),
    required_before: date | None = None,
    required_after: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
):
    items, total = orders.list_orders(
        session,
        status=order_status,
        search=search,
        required_before=required_before,
        required_after=required_after,
        limit=limit,
        offset=offset,
    )
    return OrderList(items=items, total=total)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderCreate, session: Session = Depends(get_db)):
    try:
        return orders.create_order(session, data)
    except orders.OrderValidationError as exc:
        raise _translate_error(exc) from exc


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: str, session: Session = Depends(get_db)):
    try:
        return orders.get_order(session, order_id)
    except orders.OrderNotFound as exc:
        raise _translate_error(exc) from exc


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(order_id: str, data: OrderUpdate, session: Session = Depends(get_db)):
    try:
        return orders.update_order(session, order_id, data)
    except (orders.OrderNotFound, orders.OrderValidationError) as exc:
        raise _translate_error(exc) from exc


@router.post("/{order_id}/status", response_model=OrderRead)
async def change_status(
    order_id: str, data: OrderStatusChange, session: Session = Depends(get_db)
):
    try:
        return orders.change_status(session, order_id, data.status)
    except (orders.OrderNotFound, orders.OrderValidationError) as exc:
        raise _translate_error(exc) from exc


@router.post("/{order_id}/lines", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def add_line(order_id: str, data: OrderLineCreate, session: Session = Depends(get_db)):
    try:
        return orders.add_line(session, order_id, data)
    except (orders.OrderNotFound, orders.OrderValidationError) as exc:
        raise _translate_error(exc) from exc


@router.patch("/{order_id}/lines/{line_id}", response_model=OrderRead)
async def update_line(
    order_id: str,
    line_id: str,
    data: OrderLineUpdate,
    session: Session = Depends(get_db),
):
    try:
        return orders.update_line(session, order_id, line_id, data)
    except (orders.OrderNotFound, orders.OrderValidationError) as exc:
        raise _translate_error(exc) from exc


@router.delete("/{order_id}/lines/{line_id}", response_model=OrderRead)
async def remove_line(order_id: str, line_id: str, session: Session = Depends(get_db)):
    try:
        return orders.remove_line(session, order_id, line_id)
    except (orders.OrderNotFound, orders.OrderValidationError) as exc:
        raise _translate_error(exc) from exc
