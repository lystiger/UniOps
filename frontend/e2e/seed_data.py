"""Seed the throwaway E2E database with a customer and an order that has exactly
one strong invoice candidate against the checked-in EasyBooks fixture.

Run only through the E2E harness, which points UNIOPS_DATABASE_URL at a temp
SQLite file. It adds rows through the same service functions the API uses, so
what the tests see is what the app would have produced.

Every fact (customer code, invoice date, amount) is read out of the fixture
bundle; nothing here is hard-coded.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Customer, Product
from app.schemas import CustomerCreate, OrderCreate, OrderLineCreate, ProductCreate
from app.services import catalog, order_to_cash, orders


def _guard_database_url() -> str:
    """Refuse to seed anything that is not a temp SQLite file."""
    url = get_settings().database_url
    if not url.startswith("sqlite:"):
        raise SystemExit(f"E2E seed refuses a non-sqlite database: {url}")
    path = Path(url.split("sqlite:///", 1)[-1]).resolve()
    repo_root = Path(__file__).resolve().parents[2]
    if repo_root in path.parents or path == repo_root / "uniops.db":
        raise SystemExit(f"E2E seed refuses a database inside the repository: {path}")
    return str(path)


def _trim(value: Decimal) -> Decimal:
    """Drop trailing zeros so the value satisfies the API's decimal_places limits."""
    trimmed = value.normalize()
    if trimmed == trimmed.to_integral_value():
        return trimmed.quantize(Decimal(1))
    return trimmed


def _parse_date(raw: str) -> date:
    return datetime.fromisoformat(raw).date()


def main() -> None:
    db_path = _guard_database_url()
    fixture_path = Path(sys.argv[1])
    bundle = json.loads(fixture_path.read_text())

    sale = bundle["sales_documents"][0]
    lines = bundle["sales_lines"][sale["id"]]
    line = lines[0]

    customer_code = sale["accountingObjectCode"]
    customer_name = sale["accountingObjectName"]
    invoice_date = _parse_date(sale["date"])
    subtotal = Decimal(sale["totalAmount"])
    total_amount = Decimal(sale["totalAllAmount"])

    # Reuse the fixture's own quantity and unit price when they multiply out to
    # the invoice subtotal, so the seeded order looks like the real thing.
    quantity = _trim(Decimal(line["quantity"]))
    unit_price = _trim(Decimal(line["unitPrice"]))
    if quantity * unit_price != subtotal:
        quantity, unit_price = Decimal(1), subtotal

    # A date difference of zero puts the candidate at the top of the confidence
    # scale (0.50 customer code + 0.40 amount + 0.10 same-day = 1.00).
    required_date = invoice_date
    order_date = invoice_date - timedelta(days=5)

    with SessionLocal() as session:
        # The fixture sync already mints a Customer and a Product for the codes
        # it ingests, so this is get-or-create rather than create. Either way
        # the customer ends up carrying the fixture's accounting object code,
        # which is what makes the order's invoice candidate possible.
        customer = session.scalar(
            select(Customer).where(
                Customer.easybooks_accounting_object_code == customer_code
            )
        )
        if customer is None:
            customer = catalog.create_customer(
                session,
                CustomerCreate(
                    name=customer_name,
                    tax_code=None,
                    easybooks_accounting_object_code=customer_code,
                    easybooks_source_id=None,
                ),
            )

        product_code = line["materialGoodsCode"]
        product = session.scalar(select(Product).where(Product.code == product_code))
        if product is None:
            product = catalog.create_product(
                session,
                ProductCreate(
                    code=product_code,
                    name=line["materialGoodsName"],
                    unit=line["unitName"],
                    easybooks_material_goods_id=line["materialGoodsID"],
                ),
            )

        order = orders.create_order(
            session,
            OrderCreate(
                customer_id=customer.id,
                order_date=order_date,
                required_date=required_date,
                notes="Seeded by the UniOps E2E harness.",
                lines=[
                    OrderLineCreate(
                        product_id=product.id,
                        description=line["materialGoodsName"],
                        quantity=quantity,
                        unit=line["unitName"],
                        agreed_unit_price=unit_price,
                        notes=None,
                        position=1,
                    )
                ],
            ),
        )

        # Self-check: the whole point of this order is that it has exactly one
        # strong candidate. Fail the seed rather than hand the tests a bad world.
        candidates = order_to_cash.invoice_candidates(session, order)
        if len(candidates) != 1:
            raise SystemExit(
                f"expected exactly 1 invoice candidate, got {len(candidates)}"
            )
        candidate = candidates[0]
        if not candidate.evidence.get("amount_match"):
            raise SystemExit(
                "the seeded order does not match the fixture invoice amount: "
                f"{candidate.evidence}"
            )
        if order_to_cash.auto_linkable(candidates) is None:
            raise SystemExit(
                f"the seeded candidate is not strong enough: confidence={candidate.confidence}"
            )

        facts = {
            "database_path": db_path,
            "customer_id": customer.id,
            "customer_name": customer.name,
            "customer_code": customer_code,
            "product_id": product.id,
            "product_code": product.code,
            "order_id": order.id,
            "order_number": order.order_number,
            "order_status": order.status.value,
            "order_date": order_date.isoformat(),
            "required_date": required_date.isoformat(),
            "order_total": str(quantity * unit_price),
            "line_quantity": str(quantity),
            "line_unit_price": str(unit_price),
            "invoice_source_id": candidate.source_id,
            "invoice_number": candidate.invoice_number,
            "invoice_series": candidate.invoice_series,
            "invoice_date": invoice_date.isoformat(),
            "invoice_subtotal": str(subtotal),
            "invoice_total": str(total_amount),
            "candidate_confidence": str(candidate.confidence),
        }

    out = os.environ.get("UNIOPS_E2E_FACTS_PATH")
    if out:
        Path(out).write_text(json.dumps(facts, indent=2))
    print(json.dumps(facts))


if __name__ == "__main__":
    main()
