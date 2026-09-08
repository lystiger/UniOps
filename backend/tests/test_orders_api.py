from datetime import date, timedelta


def _catalog(client):
    customer = client.post("/api/customers", json={"name": "Test Customer"}).json()
    product = client.post(
        "/api/products",
        json={"code": "TEST-PAPER", "name": "Test paper", "unit": "kg"},
    ).json()
    return customer, product


def _order_payload(customer_id, product_id):
    today = date.today()
    return {
        "customer_id": customer_id,
        "order_date": today.isoformat(),
        "required_date": (today + timedelta(days=3)).isoformat(),
        "notes": "Test order only",
        "lines": [
            {
                "product_id": product_id,
                "description": "Converted paper",
                "quantity": "125.5000",
                "unit": "kg",
                "agreed_unit_price": "24500.00",
            }
        ],
    }


def test_create_get_list_and_update_order(client):
    customer, product = _catalog(client)
    created = client.post("/api/orders", json=_order_payload(customer["id"], product["id"]))
    assert created.status_code == 201
    order = created.json()
    assert order["order_number"].startswith("UO-")
    assert order["status"] == "DRAFT"
    assert order["lines"][0]["quantity"] == "125.5000"

    fetched = client.get(f"/api/orders/{order['id']}")
    assert fetched.status_code == 200
    listed = client.get("/api/orders", params={"search": "Test Customer"})
    assert listed.json()["total"] == 1

    updated = client.patch(f"/api/orders/{order['id']}", json={"notes": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["notes"] == "Updated"


def test_order_validation_rejects_bad_dates_quantity_and_float_money(client):
    customer, product = _catalog(client)
    payload = _order_payload(customer["id"], product["id"])
    payload["required_date"] = (date.today() - timedelta(days=1)).isoformat()
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 422
    assert "required_date" in response.json()["detail"]

    payload = _order_payload(customer["id"], product["id"])
    payload["lines"][0]["quantity"] = "0"
    assert client.post("/api/orders", json=payload).status_code == 422

    payload = _order_payload(customer["id"], product["id"])
    payload["lines"][0]["agreed_unit_price"] = 24500.25
    response = client.post("/api/orders", json=payload)
    assert response.status_code == 422
    assert "not floats" in str(response.json())


def test_status_transitions_are_forward_only(client):
    customer, product = _catalog(client)
    order = client.post("/api/orders", json=_order_payload(customer["id"], product["id"])).json()

    invalid = client.post(f"/api/orders/{order['id']}/status", json={"status": "READY"})
    assert invalid.status_code == 422

    for target in (
        "CONFIRMED",
        "SCHEDULED",
        "IN_PRODUCTION",
        "READY",
        "DELIVERY_PENDING",
        "DELIVERED",
        "INVOICED",
        "CLOSED",
    ):
        response = client.post(f"/api/orders/{order['id']}/status", json={"status": target})
        assert response.status_code == 200
        assert response.json()["status"] == target

    cannot_reopen = client.post(f"/api/orders/{order['id']}/status", json={"status": "DRAFT"})
    assert cannot_reopen.status_code == 422


def test_add_update_and_remove_lines(client):
    customer, product = _catalog(client)
    order = client.post("/api/orders", json=_order_payload(customer["id"], product["id"])).json()
    added = client.post(
        f"/api/orders/{order['id']}/lines",
        json={"description": "Packing", "quantity": "2", "unit": "roll"},
    )
    assert added.status_code == 201
    second = added.json()["lines"][1]

    updated = client.patch(
        f"/api/orders/{order['id']}/lines/{second['id']}",
        json={"quantity": "3.0000"},
    )
    assert updated.status_code == 200
    assert updated.json()["lines"][1]["quantity"] == "3.0000"

    removed = client.delete(f"/api/orders/{order['id']}/lines/{second['id']}")
    assert removed.status_code == 200
    assert len(removed.json()["lines"]) == 1
    only_line_id = removed.json()["lines"][0]["id"]
    cannot_remove_last = client.delete(f"/api/orders/{order['id']}/lines/{only_line_id}")
    assert cannot_remove_last.status_code == 422
