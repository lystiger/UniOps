"""Authentication and role enforcement.

The v0.1 accepted risk was that every route was reachable by anyone who could
reach the process. These tests are what closes it, so they check the guard on
the route rather than the absence of a button in the UI.
"""

from datetime import UTC, datetime, timedelta

import pytest
from app.models import User, UserRole, UserSession
from app.security import hash_session_token
from app.services import auth
from sqlalchemy import select
from tests.conftest import ACCOUNT_PASSWORDS

GUARDED_READS = ["/api/orders", "/api/customers", "/api/products", "/api/sync-runs"]


def _new_order_payload(customer_id: str) -> dict:
    return {
        "customer_id": customer_id,
        "order_date": "2026-09-09",
        "required_date": "2026-09-12",
        "lines": [{"description": "Paper roll", "quantity": "10", "unit": "roll"}],
    }


@pytest.mark.parametrize("path", GUARDED_READS)
def test_anonymous_callers_are_refused_every_data_route(anonymous_client, path):
    response = anonymous_client.get(path)
    assert response.status_code == 401
    assert response.json()["detail"] == "sign in to use UniOps"


def test_health_stays_public_so_a_monitor_can_reach_it(anonymous_client):
    response = anonymous_client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sign_in_issues_a_restrictive_cookie_and_identifies_the_caller(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/login", json={"username": "office", "password": ACCOUNT_PASSWORDS["office"]}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "OFFICE"

    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie

    me = anonymous_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "office"


def test_only_the_cookie_digest_is_stored(session, anonymous_client):
    anonymous_client.post(
        "/api/auth/login", json={"username": "office", "password": ACCOUNT_PASSWORDS["office"]}
    )
    raw = anonymous_client.cookies["uniops_session"]
    stored = list(session.scalars(select(UserSession.token_hash)))

    assert raw not in stored
    assert hash_session_token(raw) in stored


def test_a_wrong_password_and_an_unknown_user_answer_alike(anonymous_client):
    unknown = anonymous_client.post(
        "/api/auth/login", json={"username": "nobody", "password": "not-a-password-1"}
    )
    wrong = anonymous_client.post(
        "/api/auth/login", json={"username": "office", "password": "not-a-password-1"}
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_signing_out_makes_the_cookie_unusable(client_factory):
    caller = client_factory("office")

    assert caller.post("/api/auth/logout").status_code == 204
    assert caller.get("/api/orders").status_code == 401


def test_an_expired_session_is_refused_without_being_deleted(session, client_factory):
    caller = client_factory("office")
    record = session.scalars(select(UserSession)).one()
    record.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    session.commit()

    assert caller.get("/api/orders").status_code == 401


def test_disabling_an_account_ends_its_open_sessions(session, client_factory):
    caller = client_factory("office")
    assert caller.get("/api/orders").status_code == 200

    auth.set_active(session, "office", False)

    assert caller.get("/api/orders").status_code == 401


def test_a_disabled_account_cannot_sign_in_again(session, anonymous_client):
    auth.set_active(session, "office", False)
    response = anonymous_client.post(
        "/api/auth/login", json={"username": "office", "password": ACCOUNT_PASSWORDS["office"]}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "this account is disabled"


def test_factory_read_may_read_the_board_but_not_change_it(client, factory_client):
    customer = client.post("/api/customers", json={"name": "Fixture Customer"}).json()

    assert factory_client.get("/api/orders").status_code == 200

    refused = factory_client.post("/api/orders", json=_new_order_payload(customer["id"]))
    assert refused.status_code == 403
    assert "FACTORY_READ" in refused.json()["detail"]
    assert factory_client.post("/api/customers", json={"name": "Nope"}).status_code == 403


def test_factory_read_cannot_advance_an_order(client, factory_client):
    customer = client.post("/api/customers", json={"name": "Fixture Customer"}).json()
    order = client.post("/api/orders", json=_new_order_payload(customer["id"])).json()

    response = factory_client.post(
        f"/api/orders/{order['id']}/status", json={"status": "CONFIRMED"}
    )
    assert response.status_code == 403


def test_office_may_run_the_order_desk(office_client):
    customer = office_client.post("/api/customers", json={"name": "Fixture Customer"}).json()
    created = office_client.post("/api/orders", json=_new_order_payload(customer["id"]))
    assert created.status_code == 201


def test_only_an_admin_reads_the_account_list(client, office_client, factory_client):
    assert client.get("/api/users").status_code == 200
    assert {row["username"] for row in client.get("/api/users").json()} == {
        "admin",
        "office",
        "factory",
    }
    assert office_client.get("/api/users").status_code == 403
    assert factory_client.get("/api/users").status_code == 403


def test_a_password_change_keeps_this_browser_and_drops_the_others(client_factory):
    desk = client_factory("office")
    phone = client_factory("office")

    response = desk.post(
        "/api/auth/change-password",
        json={
            "current_password": ACCOUNT_PASSWORDS["office"],
            "new_password": "a-brand-new-password",
        },
    )
    assert response.status_code == 200

    assert desk.get("/api/orders").status_code == 200
    assert phone.get("/api/orders").status_code == 401


def test_a_password_change_needs_the_current_password(client_factory):
    caller = client_factory("office")
    response = caller.post(
        "/api/auth/change-password",
        json={"current_password": "wrong-password-01", "new_password": "a-brand-new-password"},
    )
    assert response.status_code == 403
    assert caller.get("/api/orders").status_code == 200


def test_a_short_new_password_is_refused(client_factory):
    caller = client_factory("office")
    response = caller.post(
        "/api/auth/change-password",
        json={"current_password": ACCOUNT_PASSWORDS["office"], "new_password": "short"},
    )
    assert response.status_code == 422
    assert "at least 12 characters" in response.json()["detail"]


def test_accounts_are_created_case_insensitively(session, accounts):
    with pytest.raises(auth.UserExists):
        auth.create_user(
            session, username="  OFFICE ", password="another-password-1", role=UserRole.OFFICE
        )


def test_a_short_password_is_refused_at_creation(session):
    with pytest.raises(auth.WeakPassword):
        auth.create_user(session, username="newcomer", password="short", role=UserRole.OFFICE)
    assert session.scalar(select(User).where(User.username == "newcomer")) is None


def test_purging_removes_only_unusable_sessions(session, client_factory):
    live = client_factory("office")
    client_factory("admin")
    stale_record = session.scalars(
        select(UserSession).join(User).where(User.username == "admin")
    ).one()
    stale_record.expires_at = datetime.now(UTC) - timedelta(hours=1)
    session.commit()

    assert auth.purge_expired_sessions(session) == 1
    assert live.get("/api/orders").status_code == 200
