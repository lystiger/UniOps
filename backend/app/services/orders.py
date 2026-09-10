from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Customer, Order, OrderLine, OrderStatus, Product
from app.schemas import OrderCreate, OrderLineCreate, OrderLineUpdate, OrderUpdate


class OrderNotFound(LookupError):
    def __init__(
        self,
        message: str = "order not found",
        code: str = "ORDER_NOT_FOUND",
        params: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.params = params or {}


class OrderValidationError(ValueError):
    def __init__(
        self,
        message: str,
        code: str = "ORDER_VALIDATION_ERROR",
        params: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.params = params or {}


class OrderConflictError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "ORDER_CONFLICT",
        params: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.params = params or {}


ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.SCHEDULED, OrderStatus.CANCELLED},
    OrderStatus.SCHEDULED: {OrderStatus.IN_PRODUCTION, OrderStatus.CANCELLED},
    OrderStatus.IN_PRODUCTION: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.DELIVERY_PENDING, OrderStatus.CANCELLED},
    OrderStatus.DELIVERY_PENDING: {OrderStatus.DELIVERED, OrderStatus.CANCELLED},
    OrderStatus.DELIVERED: {OrderStatus.INVOICED},
    OrderStatus.INVOICED: {OrderStatus.CLOSED},
    OrderStatus.CLOSED: set(),
    OrderStatus.CANCELLED: set(),
}


def _order_query():
    return (
        select(Order)
        .execution_options(populate_existing=True)
        .options(
            selectinload(Order.customer),
            selectinload(Order.lines).selectinload(OrderLine.product),
            selectinload(Order.accounting_links),
        )
    )


def _require_customer(session: Session, customer_id: str) -> None:
    if session.get(Customer, customer_id) is None:
        raise OrderValidationError("customer does not exist", code="CUSTOMER_NOT_FOUND")


def _require_product(session: Session, product_id: str | None) -> None:
    if product_id and session.get(Product, product_id) is None:
        raise OrderValidationError("product does not exist", code="PRODUCT_NOT_FOUND")


def _validate_dates(order_date: date, required_date: date) -> None:
    if required_date < order_date:
        raise OrderValidationError(
            "required_date cannot be before order_date",
            code="REQUIRED_DATE_BEFORE_ORDER_DATE",
        )


def _new_order_number(order_date: date) -> str:
    return f"UO-{order_date:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


def get_order(session: Session, order_id: str) -> Order:
    order = session.scalar(_order_query().where(Order.id == order_id))
    if order is None:
        raise OrderNotFound("order not found", code="ORDER_NOT_FOUND")
    return order


def list_orders(
    session: Session,
    *,
    status: OrderStatus | None = None,
    search: str | None = None,
    required_before: date | None = None,
    required_after: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Order], int]:
    filters = []
    if status:
        filters.append(Order.status == status)
    if required_before:
        filters.append(Order.required_date <= required_before)
    if required_after:
        filters.append(Order.required_date >= required_after)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(Order.order_number.ilike(pattern), Order.customer.has(Customer.name.ilike(pattern)))
        )

    total = session.scalar(select(func.count(Order.id)).where(*filters)) or 0
    statement = (
        _order_query()
        .where(*filters)
        .order_by(Order.required_date, Order.created_at)
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement)), total


def create_order(session: Session, data: OrderCreate) -> Order:
    _require_customer(session, data.customer_id)
    _validate_dates(data.order_date, data.required_date)
    for line in data.lines:
        _require_product(session, line.product_id)

    order = Order(
        order_number=_new_order_number(data.order_date),
        customer_id=data.customer_id,
        status=OrderStatus.DRAFT,
        order_date=data.order_date,
        required_date=data.required_date,
        notes=data.notes,
    )
    positions: set[int] = set()
    for index, line_data in enumerate(data.lines, start=1):
        position = line_data.position or index
        if position in positions:
            raise OrderValidationError(
                "order line positions must be unique",
                code="DUPLICATE_LINE_POSITION",
            )
        positions.add(position)
        order.lines.append(_make_line(line_data, position))
    session.add(order)
    session.commit()
    return get_order(session, order.id)


def update_order(session: Session, order_id: str, data: OrderUpdate) -> Order:
    order = get_order(session, order_id)
    if order.status in {OrderStatus.CLOSED, OrderStatus.CANCELLED}:
        raise OrderValidationError(
            f"cannot update a {order.status.value} order",
            code="CANNOT_UPDATE_ORDER_STATUS",
            params={"status": order.status.value},
        )
    updates = data.model_dump(exclude_unset=True)
    customer_id = updates.get("customer_id")
    if customer_id:
        _require_customer(session, customer_id)
    order_date = updates.get("order_date", order.order_date)
    required_date = updates.get("required_date", order.required_date)
    _validate_dates(order_date, required_date)
    for key, value in updates.items():
        setattr(order, key, value)
    session.commit()
    return get_order(session, order.id)


def change_status(session: Session, order_id: str, target: OrderStatus) -> Order:
    order = get_order(session, order_id)
    if target == order.status:
        return order
    if target not in ALLOWED_TRANSITIONS[order.status]:
        raise OrderValidationError(
            f"cannot change status from {order.status.value} to {target.value}",
            code="INVALID_STATUS_TRANSITION",
            params={"from": order.status.value, "to": target.value},
        )
    if target == OrderStatus.CANCELLED and order.accounting_links:
        raise OrderConflictError(
            "cannot cancel an order with linked invoices; unlink all invoices first",
            code="ORDER_HAS_LINKED_INVOICES",
        )
    order.status = target
    session.commit()
    return get_order(session, order.id)


def add_line(session: Session, order_id: str, data: OrderLineCreate) -> Order:
    order = get_order(session, order_id)
    if order.status in {OrderStatus.CLOSED, OrderStatus.CANCELLED}:
        raise OrderValidationError(
            "cannot edit lines on a closed or cancelled order",
            code="CANNOT_EDIT_CLOSED_OR_CANCELLED_ORDER",
        )
    _require_product(session, data.product_id)
    used_positions = {line.position for line in order.lines}
    position = data.position or (max(used_positions, default=0) + 1)
    if position in used_positions:
        raise OrderValidationError(
            "order line position already exists",
            code="LINE_POSITION_EXISTS",
        )
    order.lines.append(_make_line(data, position))
    session.commit()
    return get_order(session, order.id)


def update_line(session: Session, order_id: str, line_id: str, data: OrderLineUpdate) -> Order:
    order = get_order(session, order_id)
    if order.status in {OrderStatus.CLOSED, OrderStatus.CANCELLED}:
        raise OrderValidationError(
            "cannot edit lines on a closed or cancelled order",
            code="CANNOT_EDIT_CLOSED_OR_CANCELLED_ORDER",
        )
    line = next((candidate for candidate in order.lines if candidate.id == line_id), None)
    if line is None:
        raise OrderNotFound("order line not found", code="ORDER_LINE_NOT_FOUND")
    updates = data.model_dump(exclude_unset=True)
    if "product_id" in updates:
        _require_product(session, updates["product_id"])
    if "position" in updates and any(
        item.id != line.id and item.position == updates["position"] for item in order.lines
    ):
        raise OrderValidationError(
            "order line position already exists",
            code="LINE_POSITION_EXISTS",
        )
    for key, value in updates.items():
        setattr(line, key, value)
    session.commit()
    return get_order(session, order.id)


def remove_line(session: Session, order_id: str, line_id: str) -> Order:
    order = get_order(session, order_id)
    if order.status in {OrderStatus.CLOSED, OrderStatus.CANCELLED}:
        raise OrderValidationError(
            "cannot edit lines on a closed or cancelled order",
            code="CANNOT_EDIT_CLOSED_OR_CANCELLED_ORDER",
        )
    if len(order.lines) == 1:
        raise OrderValidationError(
            "an order must have at least one line",
            code="ORDER_REQUIRES_AT_LEAST_ONE_LINE",
        )
    line = next((candidate for candidate in order.lines if candidate.id == line_id), None)
    if line is None:
        raise OrderNotFound("order line not found", code="ORDER_LINE_NOT_FOUND")
    session.delete(line)
    session.commit()
    return get_order(session, order.id)


def _make_line(data: OrderLineCreate, position: int) -> OrderLine:
    values = data.model_dump(exclude={"position"})
    return OrderLine(**values, position=position)
