from datetime import date, timedelta
from decimal import Decimal

from app.models import SalesDocument
from app.services import analytics, auth, catalog, order_to_cash, orders


def _catalog(client):
    c_res = client.post("/api/customers", json={"name": "Err Test Co", "tax_code": "0109999999"})
    p_res = client.post(
        "/api/products", json={"code": "ERR-P1", "name": "Err Product 1", "unit": "box"}
    )
    return c_res.json(), p_res.json()


def _order_payload(customer_id: str, product_id: str):
    today = date.today()
    return {
        "customer_id": customer_id,
        "order_date": today.isoformat(),
        "required_date": (today + timedelta(days=7)).isoformat(),
        "notes": "Error test order",
        "lines": [
            {
                "product_id": product_id,
                "description": "Err box",
                "quantity": "50",
                "unit": "box",
                "agreed_unit_price": "25000",
                "notes": "Line 1",
            }
        ],
    }


def test_auth_errors(client, client_factory):
    # 1. Unauthenticated request -> 401 AUTH_REQUIRED
    anon = client_factory()
    res_anon = anon.get("/api/orders")
    assert res_anon.status_code == 401
    body_anon = res_anon.json()
    assert body_anon["code"] == "AUTH_REQUIRED"

    # 2. Login with bad credentials -> 401 INVALID_CREDENTIALS
    res = client.post(
        "/api/auth/login",
        json={"username": "nonexistent", "password": "wrongpassword123"},
    )
    assert res.status_code == 401
    body = res.json()
    assert body["code"] == "INVALID_CREDENTIALS"
    assert "detail" in body

    # 3. Change password with incorrect current password -> 403 INVALID_CURRENT_PASSWORD
    res2 = client.post(
        "/api/auth/change-password",
        json={"current_password": "wrongpassword123", "new_password": "validnewpassword123"},
    )
    assert res2.status_code == 403
    body2 = res2.json()
    assert body2["code"] == "INVALID_CURRENT_PASSWORD"

    # 4. WeakPassword service error has code
    weak_err = auth.WeakPassword("password must be at least 12 characters")
    assert weak_err.code == "WEAK_PASSWORD"


def test_role_refused_error(client, client_factory):
    factory_client = client_factory("factory")
    customer, product = _catalog(client)
    payload = _order_payload(customer["id"], product["id"])

    res = factory_client.post("/api/orders", json=payload)
    assert res.status_code == 403
    body = res.json()
    assert body["code"] == "PERMISSION_DENIED"
    assert body["params"]["role"] == "FACTORY_READ"


def test_catalog_conflict_errors(client):
    customer, product = _catalog(client)
    # Duplicate product code -> 409 PRODUCT_CODE_EXISTS
    res = client.post(
        "/api/products", json={"code": product["code"], "name": "Duplicate Product", "unit": "box"}
    )
    assert res.status_code == 409
    assert res.json()["code"] == "PRODUCT_CODE_EXISTS"


def test_order_validation_errors(client):
    customer, product = _catalog(client)

    # 1. Required date before order date -> REQUIRED_DATE_BEFORE_ORDER_DATE
    payload = _order_payload(customer["id"], product["id"])
    payload["required_date"] = (date.today() - timedelta(days=1)).isoformat()
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 422
    assert res.json()["code"] == "REQUIRED_DATE_BEFORE_ORDER_DATE"

    # 2. Duplicate line positions -> DUPLICATE_LINE_POSITION
    payload2 = _order_payload(customer["id"], product["id"])
    payload2["lines"][0]["position"] = 1
    payload2["lines"].append(
        {
            "product_id": product["id"],
            "description": "Line 2",
            "quantity": "10",
            "unit": "box",
            "agreed_unit_price": "1000",
            "position": 1,
        }
    )
    res2 = client.post("/api/orders", json=payload2)
    assert res2.status_code == 422
    assert res2.json()["code"] == "DUPLICATE_LINE_POSITION"

    # 3. Invalid status transition -> INVALID_STATUS_TRANSITION
    valid_payload = _order_payload(customer["id"], product["id"])
    order = client.post("/api/orders", json=valid_payload).json()
    res3 = client.post(f"/api/orders/{order['id']}/status", json={"status": "DELIVERED"})
    assert res3.status_code == 422
    body3 = res3.json()
    assert body3["code"] == "INVALID_STATUS_TRANSITION"
    assert body3["params"]["from"] == "DRAFT"
    assert body3["params"]["to"] == "DELIVERED"


def test_order_cancellation_conflict_error(client, session):
    customer, product = _catalog(client)
    order = client.post("/api/orders", json=_order_payload(customer["id"], product["id"])).json()

    doc = SalesDocument(
        source_id="INV-ERR-TEST",
        document_date=date(2026, 8, 2),
        source_type="SA_INVOICE",
        invoice_number="INV-ERR-01",
        invoice_series="1C26TSH",
        accounting_object_code="KH-TEST",
        accounting_object_name="Test Customer",
        subtotal=Decimal("10000.00"),
        vat_amount=Decimal("1000.00"),
        total_amount=Decimal("11000.00"),
        currency_id="VND",
        normalized_hash="hash_err_test",
    )
    session.add(doc)
    session.commit()

    link_res = client.post(
        f"/api/orders/{order['id']}/invoice-links",
        json={"sales_document_id": doc.id},
    )
    assert link_res.status_code == 201

    cancel_res = client.post(
        f"/api/orders/{order['id']}/status",
        json={"status": "CANCELLED"},
    )
    assert cancel_res.status_code == 409
    body = cancel_res.json()
    assert body["code"] == "ORDER_HAS_LINKED_INVOICES"


def test_analytics_invalid_window_error(client):
    res = client.get("/api/analytics/overview?from_date=2026-08-30&to_date=2026-08-01")
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "INVALID_DATE_WINDOW"
    assert body["params"]["from_date"] == "2026-08-30"
    assert body["params"]["to_date"] == "2026-08-01"


def test_service_error_classes_have_code_and_params():
    """Verify that every service error class has a code attribute and params dict."""
    error_classes = [
        orders.OrderNotFound("not found"),
        orders.OrderValidationError("invalid", code="TEST_VALIDATION"),
        orders.OrderConflictError("conflict", code="TEST_CONFLICT"),
        order_to_cash.LinkError("link err"),
        order_to_cash.LinkNotFound("link not found"),
        auth.AuthError("auth err"),
        auth.UserExists("exists"),
        auth.UserNotFound("not found"),
        auth.WeakPassword("weak"),
        catalog.CatalogConflict("conflict"),
        analytics.InvalidDateWindow("invalid window"),
        analytics.CustomerNotFound("customer not found"),
    ]
    for exc in error_classes:
        assert hasattr(exc, "code")
        assert isinstance(exc.code, str)
        assert hasattr(exc, "params")
        assert isinstance(exc.params, dict)
