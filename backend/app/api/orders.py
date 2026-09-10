from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import WRITE_ROLES, read_access, require_roles, write_access
from app.database import get_db
from app.errors import ApiError
from app.models import OrderStatus, User
from app.schemas import (
    InvoiceCandidateRead,
    InvoiceLinkCreate,
    OrderAccountingRead,
    OrderCreate,
    OrderLineCreate,
    OrderLineUpdate,
    OrderList,
    OrderRead,
    OrderStatusChange,
    OrderUpdate,
)
from app.services import order_to_cash, orders

router = APIRouter(prefix="/orders", tags=["orders"])


def _translate_error(exc: Exception) -> ApiError:
    code = getattr(exc, "code", "ORDER_ERROR")
    params = getattr(exc, "params", {})
    if isinstance(exc, orders.OrderNotFound):
        return ApiError(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc), code=code, params=params
        )
    if isinstance(exc, orders.OrderConflictError):
        return ApiError(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc), code=code, params=params
        )
    return ApiError(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
        code=code,
        params=params,
    )


@router.get("", response_model=OrderList, dependencies=[read_access])
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
    # The board shows an accounting badge per card. Resolved in bulk here rather
    # than per card, and never stored on the order: it is derived state.
    read = [OrderRead.model_validate(order) for order in items]
    statuses = order_to_cash.accounting_status_by_order(session, items)
    for entry in read:
        entry.accounting_status = statuses.get(entry.id)
    return OrderList(items=read, total=total)


@router.post(
    "", response_model=OrderRead, status_code=status.HTTP_201_CREATED,
    dependencies=[write_access],
)
async def create_order(data: OrderCreate, session: Session = Depends(get_db)):
    try:
        return orders.create_order(session, data)
    except orders.OrderValidationError as exc:
        raise _translate_error(exc) from exc


@router.get("/{order_id}", response_model=OrderRead, dependencies=[read_access])
async def get_order(order_id: str, session: Session = Depends(get_db)):
    try:
        return orders.get_order(session, order_id)
    except orders.OrderNotFound as exc:
        raise _translate_error(exc) from exc


@router.patch("/{order_id}", response_model=OrderRead, dependencies=[write_access])
async def update_order(order_id: str, data: OrderUpdate, session: Session = Depends(get_db)):
    try:
        return orders.update_order(session, order_id, data)
    except (orders.OrderNotFound, orders.OrderValidationError) as exc:
        raise _translate_error(exc) from exc


@router.post("/{order_id}/status", response_model=OrderRead, dependencies=[write_access])
async def change_status(
    order_id: str, data: OrderStatusChange, session: Session = Depends(get_db)
):
    try:
        return orders.change_status(session, order_id, data.status)
    except (orders.OrderNotFound, orders.OrderValidationError, orders.OrderConflictError) as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/{order_id}/lines", response_model=OrderRead, status_code=status.HTTP_201_CREATED,
    dependencies=[write_access],
)
async def add_line(order_id: str, data: OrderLineCreate, session: Session = Depends(get_db)):
    try:
        return orders.add_line(session, order_id, data)
    except (orders.OrderNotFound, orders.OrderValidationError) as exc:
        raise _translate_error(exc) from exc


@router.patch(
    "/{order_id}/lines/{line_id}", response_model=OrderRead, dependencies=[write_access]
)
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


@router.delete(
    "/{order_id}/lines/{line_id}", response_model=OrderRead, dependencies=[write_access]
)
async def remove_line(order_id: str, line_id: str, session: Session = Depends(get_db)):
    try:
        return orders.remove_line(session, order_id, line_id)
    except (orders.OrderNotFound, orders.OrderValidationError) as exc:
        raise _translate_error(exc) from exc


def _order_or_404(session: Session, order_id: str):
    try:
        return orders.get_order(session, order_id)
    except orders.OrderNotFound as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
            code=getattr(exc, "code", "ORDER_NOT_FOUND"),
            params={"order_id": order_id},
        ) from exc


@router.get(
    "/{order_id}/accounting", response_model=OrderAccountingRead, dependencies=[read_access]
)
async def order_accounting(order_id: str, session: Session = Depends(get_db)):
    """The derived accounting picture of one order. Reads EasyBooks data only."""
    return order_to_cash.accounting_for(session, _order_or_404(session, order_id))


@router.get(
    "/{order_id}/invoice-candidates",
    response_model=list[InvoiceCandidateRead],
    dependencies=[read_access],
)
async def invoice_candidates(order_id: str, session: Session = Depends(get_db)):
    """Invoices that could be this order, scored and explained. Creates nothing."""
    return order_to_cash.invoice_candidates(session, _order_or_404(session, order_id))


@router.post(
    "/{order_id}/invoice-links",
    response_model=OrderAccountingRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice_link(
    order_id: str,
    data: InvoiceLinkCreate,
    session: Session = Depends(get_db),
    user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """Confirm that this order became this invoice.

    Records who confirmed it and the evidence at the time. Writes nothing to
    EasyBooks.
    """
    order = _order_or_404(session, order_id)
    try:
        order_to_cash.create_link(session, order, data.sales_document_id, user)
    except order_to_cash.LinkNotFound as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
            code=getattr(exc, "code", "SALES_DOCUMENT_NOT_FOUND"),
            params=getattr(exc, "params", {}),
        ) from exc
    except order_to_cash.LinkError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
            code=getattr(exc, "code", "LINK_ERROR"),
            params=getattr(exc, "params", {}),
        ) from exc
    return order_to_cash.accounting_for(session, order)


@router.delete("/{order_id}/invoice-links/{link_id}", response_model=OrderAccountingRead)
async def delete_invoice_link(
    order_id: str,
    link_id: str,
    session: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
):
    """Remove the UniOps relationship. EasyBooks is not touched."""
    order = _order_or_404(session, order_id)
    try:
        order_to_cash.delete_link(session, order, link_id)
    except order_to_cash.LinkNotFound as exc:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
            code=getattr(exc, "code", "LINK_NOT_FOUND"),
            params=getattr(exc, "params", {}),
        ) from exc
    return order_to_cash.accounting_for(session, order)
