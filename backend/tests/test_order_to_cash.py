"""Order-to-cash: linking UniOps orders to EasyBooks invoices, and what follows.

EasyBooks stays the accounting system of record throughout. Nothing here writes
to it, and every accounting state is derived rather than stored.
"""

from datetime import date
from decimal import Decimal

import pytest
from app.integrations.easybooks.reconciliation import check_integrity
from app.integrations.easybooks.sync import FixtureBundle, sync_bundle
from app.models import (
    Customer,
    LinkMethod,
    Order,
    OrderAccountingLink,
    OrderStatus,
    SalesDocument,
)
from app.schemas import OrderCreate, OrderLineCreate
from app.services import exceptions_view, order_to_cash, orders
from sqlalchemy import func, select

CUSTOMER_CODE = "0101394777-024"
OTHER_CODE = "0100000000-001"


def _invoice(source_id: str, day: str, subtotal: str, code: str = CUSTOMER_CODE) -> dict:
    """A sales header shaped like the observed live payload."""
    return {
        "id": source_id,
        "date": day,
        "typeID": 320,
        "typeName": "Bán hàng chưa thu tiền",
        "invoiceNo": source_id.upper(),
        "invoiceSeries": "1C26TSH",
        "accountingObjectCode": code,
        "accountingObjectName": f"Customer {code}",
        "totalAmount": subtotal,
        "totalVATAmount": "0.00",
        "totalAllAmount": subtotal,
    }


def _sync_invoices(session, *documents) -> None:
    sync_bundle(
        session,
        FixtureBundle(
            sales_documents=list(documents), sales_lines={}, sales_lines_available=False
        ),
    )


def _customer(session, code: str = CUSTOMER_CODE, name: str = "Fixture Customer") -> Customer:
    customer = Customer(name=name, easybooks_accounting_object_code=code)
    session.add(customer)
    session.commit()
    return customer


def _order(session, customer, required: str, unit_price: str | None = "1000.00") -> Order:
    return orders.create_order(
        session,
        OrderCreate(
            customer_id=customer.id,
            order_date=date.fromisoformat(required),
            required_date=date.fromisoformat(required),
            lines=[
                OrderLineCreate(
                    description="Paper reel",
                    quantity=Decimal("10"),
                    unit="roll",
                    agreed_unit_price=Decimal(unit_price) if unit_price else None,
                )
            ],
        ),
    )


def _advance_to(session, order: Order, target: OrderStatus) -> Order:
    chain = [
        OrderStatus.CONFIRMED,
        OrderStatus.SCHEDULED,
        OrderStatus.IN_PRODUCTION,
        OrderStatus.READY,
        OrderStatus.DELIVERY_PENDING,
        OrderStatus.DELIVERED,
    ]
    for step in chain:
        order = orders.change_status(session, order.id, step)
        if step == target:
            break
    return order


# --- matching ---------------------------------------------------------------


def test_one_obvious_invoice_becomes_a_scored_candidate(session):
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-02", "10000.00"))
    order = _order(session, customer, "2026-03-01")

    candidates = order_to_cash.invoice_candidates(session, order)

    assert len(candidates) == 1
    only = candidates[0]
    assert only.evidence["customer_code_match"] is True
    assert only.evidence["amount_match"] is True
    assert only.evidence["date_difference_days"] == 1
    assert only.confidence == Decimal("1.0")
    assert order_to_cash.auto_linkable(candidates) is only


def test_two_plausible_invoices_are_never_auto_linked(session):
    customer = _customer(session)
    _sync_invoices(
        session,
        _invoice("inv-1", "2026-03-02", "10000.00"),
        _invoice("inv-2", "2026-03-03", "10000.00"),
    )
    order = _order(session, customer, "2026-03-01")

    candidates = order_to_cash.invoice_candidates(session, order)

    assert len(candidates) == 2
    # Ambiguity is handed back, not resolved by picking the higher score.
    assert order_to_cash.auto_linkable(candidates) is None


def test_a_different_customer_is_not_a_candidate(session):
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-02", "10000.00", code=OTHER_CODE))
    order = _order(session, customer, "2026-03-01")

    assert order_to_cash.invoice_candidates(session, order) == []


def test_an_invoice_outside_the_date_window_is_not_a_candidate(session):
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-05-01", "10000.00"))
    order = _order(session, customer, "2026-03-01")

    assert order_to_cash.invoice_candidates(session, order) == []


def test_an_amount_mismatch_lowers_confidence_below_the_auto_threshold(session):
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "99999.00"))
    order = _order(session, customer, "2026-03-01")

    candidates = order_to_cash.invoice_candidates(session, order)

    assert candidates[0].evidence["amount_match"] is False
    assert candidates[0].confidence < order_to_cash.AUTO_LINK_CONFIDENCE
    assert order_to_cash.auto_linkable(candidates) is None


def test_an_order_without_agreed_prices_never_claims_an_amount_match(session):
    """A missing price makes the order's value unknown, and unknown is not a match."""
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "10000.00"))
    order = _order(session, customer, "2026-03-01", unit_price=None)

    candidates = order_to_cash.invoice_candidates(session, order)

    assert order_to_cash.order_total(order) is None
    assert candidates[0].evidence["amount_match"] is False
    assert order_to_cash.auto_linkable(candidates) is None


def test_a_customer_without_an_easybooks_code_has_no_candidates(session):
    customer = Customer(name="Not in EasyBooks")
    session.add(customer)
    session.commit()
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "10000.00"))
    order = _order(session, customer, "2026-03-01")

    assert order_to_cash.invoice_candidates(session, order) == []


# --- manual linking and permissions ----------------------------------------


def _linkable(session):
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "10000.00"))
    order = _order(session, customer, "2026-03-01")
    document = session.scalar(select(SalesDocument))
    return order, document


def test_office_can_confirm_a_link_and_it_records_who_and_why(session, office_client):
    order, document = _linkable(session)

    response = office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["accounting_status"] == "INVOICED"
    invoice = body["invoices"][0]
    assert invoice["created_by"] == "office"
    assert invoice["link_method"] == "CUSTOMER_DATE_AMOUNT"
    assert invoice["confidence"] == "1.0000"
    assert invoice["evidence"]["amount_match"] is True


def test_a_link_made_on_weak_evidence_says_so(session, office_client):
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "77777.00"))
    order = _order(session, customer, "2026-03-01")
    document = session.scalar(select(SalesDocument))

    office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )

    link = session.scalar(select(OrderAccountingLink))
    assert link.link_method == LinkMethod.MANUAL
    assert link.evidence["amount_match"] is False
    assert link.created_by_user_id is not None


def test_factory_read_may_see_accounting_but_not_change_it(session, factory_client):
    order, document = _linkable(session)

    assert factory_client.get(f"/api/orders/{order.id}/accounting").status_code == 200
    assert factory_client.get(f"/api/orders/{order.id}/invoice-candidates").status_code == 200
    refused = factory_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )
    assert refused.status_code == 403


def test_an_anonymous_caller_reaches_none_of_it(session, anonymous_client):
    order, document = _linkable(session)

    assert anonymous_client.get(f"/api/orders/{order.id}/accounting").status_code == 401
    assert anonymous_client.get("/api/analytics/receivables").status_code == 401
    assert anonymous_client.get("/api/operations/exceptions").status_code == 401


def test_the_same_pair_cannot_be_linked_twice(session, office_client):
    order, document = _linkable(session)
    payload = {"sales_document_id": document.id}

    first = office_client.post(f"/api/orders/{order.id}/invoice-links", json=payload)
    assert first.status_code == 201
    duplicate = office_client.post(f"/api/orders/{order.id}/invoice-links", json=payload)

    assert duplicate.status_code == 409
    assert session.scalar(select(func.count()).select_from(OrderAccountingLink)) == 1


def test_one_order_may_link_to_several_invoices(session, office_client):
    """Cardinality is open: an order can split across invoices."""
    customer = _customer(session)
    _sync_invoices(
        session,
        _invoice("inv-1", "2026-03-01", "4000.00"),
        _invoice("inv-2", "2026-03-02", "6000.00"),
    )
    order = _order(session, customer, "2026-03-01")

    for document in session.scalars(select(SalesDocument)):
        office_client.post(
            f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
        )

    accounting = order_to_cash.accounting_for(session, orders.get_order(session, order.id))
    assert len(accounting.invoices) == 2
    assert accounting.accounting_status == order_to_cash.AccountingStatus.INVOICED


def test_unlinking_removes_only_the_uniops_relationship(session, office_client):
    order, document = _linkable(session)
    created = office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    ).json()
    link_id = created["invoices"][0]["link_id"]

    response = office_client.delete(f"/api/orders/{order.id}/invoice-links/{link_id}")

    assert response.status_code == 200
    assert response.json()["accounting_status"] in {"NOT_INVOICED", "INVOICE_CANDIDATE"}
    assert session.scalar(select(func.count()).select_from(OrderAccountingLink)) == 0
    # The EasyBooks-derived invoice is untouched.
    assert session.get(SalesDocument, document.id) is not None


def test_linking_an_unknown_invoice_is_a_404(session, office_client):
    order, _ = _linkable(session)
    response = office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": "nope"}
    )
    assert response.status_code == 404


# --- derived state ----------------------------------------------------------


def test_accounting_state_moves_from_not_invoiced_to_candidate_to_invoiced(
    session, office_client
):
    customer = _customer(session)
    order = _order(session, customer, "2026-03-01")

    fresh = order_to_cash.accounting_for(session, order)
    assert fresh.accounting_status == order_to_cash.AccountingStatus.NOT_INVOICED

    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "10000.00"))
    order = orders.get_order(session, order.id)
    assert (
        order_to_cash.accounting_for(session, order).accounting_status
        == order_to_cash.AccountingStatus.INVOICE_CANDIDATE
    )

    document = session.scalar(select(SalesDocument))
    office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )
    assert (
        order_to_cash.accounting_for(session, orders.get_order(session, order.id)).accounting_status
        == order_to_cash.AccountingStatus.INVOICED
    )


def test_payment_and_due_state_stay_unknown_because_easybooks_says_nothing(
    session, office_client
):
    order, document = _linkable(session)
    body = office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    ).json()

    assert body["payment_status"] == "UNKNOWN"
    assert body["outstanding_amount"] is None
    assert "no paid or outstanding amount" in body["outstanding_status"]
    invoice = body["invoices"][0]
    assert invoice["payment_status"] == "UNKNOWN"
    assert invoice["due_date"] is None
    assert invoice["due_status"] == "UNKNOWN"


def test_an_invoice_without_a_due_date_is_never_reported_overdue(session, office_client):
    order, document = _linkable(session)
    office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )

    receivables = office_client.get("/api/analytics/receivables").json()

    assert receivables["total_overdue"] is None
    assert receivables["overdue_invoice_count"] is None
    assert "no due date" in receivables["due_status"]


def test_the_order_status_enum_is_not_overloaded_with_payment_states(session):
    """Production lifecycle and accounting state are separate machines."""
    values = {status.value for status in OrderStatus}
    assert not values & {"PAID", "PARTIALLY_PAID", "OVERDUE", "UNPAID"}


def test_the_board_carries_a_derived_accounting_badge(session, client):
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "10000.00"))
    _order(session, customer, "2026-03-01")

    body = client.get("/api/orders").json()

    assert body["items"][0]["accounting_status"] == "INVOICE_CANDIDATE"


# --- receivables ------------------------------------------------------------


def test_receivables_report_what_is_invoiced_and_refuse_to_guess_the_rest(session, client):
    _customer(session)
    _sync_invoices(
        session,
        _invoice("inv-1", "2026-03-01", "10000.00"),
        _invoice("inv-2", "2026-03-05", "25000.00"),
        _invoice("inv-3", "2026-03-06", "5000.00", code=OTHER_CODE),
    )

    body = client.get("/api/analytics/receivables").json()

    assert body["invoice_count"] == 3
    assert body["total_invoiced"] == "40000.00"
    assert body["total_outstanding"] is None
    assert body["unpaid_invoice_count"] is None
    assert body["unlinked_invoice_count"] == 3
    by_code = {row["customer_code"]: row for row in body["customers"]}
    assert by_code[CUSTOMER_CODE]["total_invoiced"] == "35000.00"
    assert by_code[CUSTOMER_CODE]["invoice_count"] == 2
    assert by_code[CUSTOMER_CODE]["outstanding_amount"] is None
    assert by_code[OTHER_CODE]["total_invoiced"] == "5000.00"


def test_receivables_money_never_crosses_the_wire_as_a_float(session, client):
    _customer(session)
    _sync_invoices(
        session,
        _invoice("inv-1", "2026-03-01", "0.10"),
        _invoice("inv-2", "2026-03-02", "0.20"),
    )

    body = client.get("/api/analytics/receivables").json()

    assert isinstance(body["total_invoiced"], str)
    assert body["total_invoiced"] == "0.30"


def test_a_customer_receivable_lists_invoices_and_the_orders_linked_to_them(
    session, office_client
):
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "10000.00"))
    order = _order(session, customer, "2026-03-01")
    document = session.scalar(select(SalesDocument))
    office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )

    body = office_client.get(f"/api/customers/{customer.id}/receivables").json()

    assert body["invoice_count"] == 1
    assert body["total_invoiced"] == "10000.00"
    assert body["total_outstanding"] is None
    invoice = body["invoices"][0]
    assert invoice["linked_order_numbers"] == [order.order_number]
    assert invoice["paid_amount"] is None
    assert invoice["payment_status"] == "UNKNOWN"


def test_an_unknown_customer_receivable_is_a_404(session, client):
    assert client.get("/api/customers/nope/receivables").status_code == 404


# --- exceptions -------------------------------------------------------------


def test_a_delivered_order_with_no_invoice_is_an_exception(session, client):
    customer = _customer(session)
    order = _order(session, customer, "2026-03-01")
    _advance_to(session, order, OrderStatus.DELIVERED)

    body = client.get("/api/operations/exceptions").json()
    groups = {group["category"]: group for group in body["groups"]}

    assert groups["DELIVERED_ORDER_NOT_INVOICED"]["count"] == 1
    assert groups["DELIVERED_ORDER_NOT_INVOICED"]["items"][0]["reference"] == order.order_number


def test_an_invoice_linked_to_nothing_is_an_exception(session, client):
    _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "10000.00"))

    groups = {g["category"]: g for g in client.get("/api/operations/exceptions").json()["groups"]}

    assert groups["INVOICE_WITHOUT_ORDER"]["count"] == 1


def test_ambiguous_candidates_are_surfaced_for_a_person_to_resolve(session, client):
    customer = _customer(session)
    _sync_invoices(
        session,
        _invoice("inv-1", "2026-03-01", "10000.00"),
        _invoice("inv-2", "2026-03-02", "10000.00"),
    )
    order = _order(session, customer, "2026-03-01")
    _advance_to(session, order, OrderStatus.DELIVERED)

    groups = {g["category"]: g for g in client.get("/api/operations/exceptions").json()["groups"]}

    assert groups["AMBIGUOUS_INVOICE_CANDIDATES"]["count"] == 1


def test_every_category_is_always_reported_even_when_empty(session, client):
    body = client.get("/api/operations/exceptions").json()

    assert {group["category"] for group in body["groups"]} == {
        category.value for category in exceptions_view.ExceptionCategory
    }
    assert body["total"] == 0


def test_a_linked_amount_difference_is_evidence_not_a_sync_failure(session, office_client):
    """Freight, tax, discounts and split invoices all explain a difference."""
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "77777.00"))
    order = _order(session, customer, "2026-03-01")
    document = session.scalar(select(SalesDocument))
    office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )

    groups = {
        g["category"]: g
        for g in office_client.get("/api/operations/exceptions").json()["groups"]
    }
    assert groups["LINKED_AMOUNT_MISMATCH"]["count"] == 1
    # Reported to a person, not counted as a broken pipeline.
    assert check_integrity(session).warnings == []


# --- reconciliation ---------------------------------------------------------


def test_a_link_joining_two_different_customers_raises_a_warning(session, office_client):
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "10000.00", code=OTHER_CODE))
    order = _order(session, customer, "2026-03-01")
    document = session.scalar(select(SalesDocument))

    office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )

    report = check_integrity(session)
    assert report.accounting_links_with_customer_mismatch == 1
    assert any("different customers" in warning for warning in report.warnings)
    groups = {
        g["category"]: g
        for g in office_client.get("/api/operations/exceptions").json()["groups"]
    }
    assert groups["LINKED_CUSTOMER_MISMATCH"]["count"] == 1


def test_a_customer_mismatch_is_counted_on_the_next_sync(session, office_client):
    customer = _customer(session)
    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "10000.00", code=OTHER_CODE))
    order = _order(session, customer, "2026-03-01")
    document = session.scalar(select(SalesDocument))
    office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )

    run = sync_bundle(session, FixtureBundle())

    assert run.reconciliation_warnings == 1


def test_links_survive_a_resync_and_stay_attached_to_the_same_invoice(session, office_client):
    order, document = _linkable(session)
    office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )

    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "10000.00"))

    link = session.scalar(select(OrderAccountingLink))
    assert link.sales_document_id == document.id
    assert session.scalar(select(func.count()).select_from(OrderAccountingLink)) == 1


def test_a_corrected_invoice_updates_the_receivable_without_relinking(session, office_client):
    """Accounting facts change. The link is ours; the amount is EasyBooks'."""
    order, document = _linkable(session)
    office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )
    before = office_client.get("/api/analytics/receivables").json()["total_invoiced"]

    _sync_invoices(session, _invoice("inv-1", "2026-03-01", "12345.00"))

    after = office_client.get("/api/analytics/receivables").json()["total_invoiced"]
    assert before == "10000.00"
    assert after == "12345.00"
    assert session.scalar(select(func.count()).select_from(OrderAccountingLink)) == 1


@pytest.mark.parametrize(
    "path",
    ["/api/analytics/receivables", "/api/operations/exceptions"],
)
def test_the_new_read_models_expose_no_write_route(client, path):
    assert client.post(path, json={}).status_code == 405


def test_cannot_link_invoice_to_cancelled_order(session, office_client):
    order, document = _linkable(session)
    order.status = OrderStatus.CANCELLED
    session.commit()

    response = office_client.post(
        f"/api/orders/{order.id}/invoice-links", json={"sales_document_id": document.id}
    )
    assert response.status_code == 409
    assert "cannot link an invoice to a cancelled order" in response.json()["detail"]


def test_invoice_without_order_respects_tracking_date_and_carries_customer_name(session):
    _sync_invoices(
        session,
        _invoice("inv-old", "2026-01-15", "1000.00"),
        _invoice("inv-on", "2026-06-01", "1500.00"),
        _invoice("inv-new", "2026-07-01", "2000.00"),
    )
    # Undated document
    doc_undated = SalesDocument(
        source_id="inv-undated",
        source_system="easybooks",
        invoice_number="UNDATED1",
        invoice_series="1C26TSH",
        accounting_object_name="Undated Customer",
        total_amount=Decimal("3000.00"),
        document_date=None,
        normalized_hash="hash-undated",
    )
    session.add(doc_undated)
    session.commit()

    cat = exceptions_view.ExceptionCategory.INVOICE_WITHOUT_ORDER
    # 1. When tracking date is unset (None): all 4 documents are reported
    rep_all = exceptions_view.report(session, order_tracking_since=None)
    items_all = next(g.items for g in rep_all.groups if g.category == cat)
    assert len(items_all) == 4

    # 2. When tracking date is 2026-06-01:
    # - inv-old (2026-01-15) is excluded (< 2026-06-01)
    # - inv-on (2026-06-01) is included (== 2026-06-01)
    # - inv-new (2026-07-01) is included (> 2026-06-01)
    # - inv-undated (None) is included (undated documents are never silently dropped)
    rep_filtered = exceptions_view.report(session, order_tracking_since=date(2026, 6, 1))
    items_filtered = next(g.items for g in rep_filtered.groups if g.category == cat)
    assert len(items_filtered) == 3

    # Check structure, reference format, customer name, date, and amount
    new_item = next(i for i in items_filtered if i.document_date == date(2026, 7, 1))
    assert new_item.reference == "Invoice 1C26TSH/INV-NEW"
    assert new_item.customer_name == f"Customer {CUSTOMER_CODE}"
    assert new_item.detail == "Invoice not linked to any UniOps order"
    assert new_item.total_amount == Decimal("2000.00")
    assert new_item.document_date == date(2026, 7, 1)

    undated_item = next(i for i in items_filtered if i.document_date is None)
    assert undated_item.reference == "Invoice 1C26TSH/UNDATED1"
    assert undated_item.customer_name == "Undated Customer"
    assert undated_item.total_amount == Decimal("3000.00")


def test_exceptions_report_defaults_as_of_to_business_today(session):
    from app.integrations.easybooks.client import business_today

    rep = exceptions_view.report(session)
    assert rep.as_of == business_today()


def test_exceptions_api_supports_order_tracking_since(session, office_client):
    _sync_invoices(
        session,
        _invoice("inv-old2", "2026-01-15", "1000.00"),
        _invoice("inv-new2", "2026-07-01", "2000.00"),
    )

    # Without query param: both returned
    resp = office_client.get("/api/operations/exceptions")
    assert resp.status_code == 200
    group = next(g for g in resp.json()["groups"] if g["category"] == "INVOICE_WITHOUT_ORDER")
    assert group["count"] == 2

    # With query param: only 2026-07-01 returned
    url = "/api/operations/exceptions?order_tracking_since=2026-06-01"
    resp_filtered = office_client.get(url)
    assert resp_filtered.status_code == 200
    groups = resp_filtered.json()["groups"]
    group_filtered = next(g for g in groups if g["category"] == "INVOICE_WITHOUT_ORDER")
    assert group_filtered["count"] == 1
    assert group_filtered["items"][0]["reference"] == "Invoice 1C26TSH/INV-NEW2"
    assert group_filtered["items"][0]["customer_name"] == f"Customer {CUSTOMER_CODE}"
    assert group_filtered["items"][0]["document_date"] == "2026-07-01"

