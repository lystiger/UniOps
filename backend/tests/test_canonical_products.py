"""The canonical product master: SKU allocation, lifecycle, and who may touch it."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from app.config import get_settings
from app.integrations.easybooks.contracts import CatalogItem
from app.integrations.easybooks.sync import _catalog_product, sync_bundle
from app.models import Product, ProductSkuSequence
from app.schemas import ProductCreate, ProductUpdate
from app.services import catalog
from pydantic import SecretStr, ValidationError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

SERVICE_KEY = "k" * 40


def _create(session, name: str = "Jumbo roll 700g 2-ply", **fields) -> Product:
    return catalog.create_product(session, ProductCreate(name=name, unit="Cuộn", **fields))


# SKU allocation ------------------------------------------------------------


def test_skus_are_sequential_non_semantic_and_start_at_one(session):
    first = _create(session, "Napkin 2-ply", specifications={"ply": 2})
    second = _create(session, "Napkin 3-ply", specifications={"ply": 3})
    third = _create(session, "Hand towel 175g")

    assert [first.sku, second.sku, third.sku] == ["UG000001", "UG000002", "UG000003"]
    assert all(catalog.SKU_PATTERN.match(p.sku) for p in (first, second, third))


def test_a_committed_sku_is_never_handed_out_again(session):
    product = _create(session)
    session.execute(delete(Product).where(Product.id == product.id))
    session.commit()

    assert _create(session, "Replacement").sku == "UG000002"


def test_a_rolled_back_creation_does_not_consume_a_number(session):
    catalog.allocate_sku(session)
    session.rollback()

    assert _create(session).sku == "UG000001"


def test_the_database_rejects_a_duplicate_sku(session):
    _create(session)
    session.add(Product(sku="UG000001", name="Copy", unit="Cuộn"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


@pytest.mark.parametrize("sku", ["XX000001", "UG1", "UG0000001"])
def test_the_database_rejects_a_malformed_sku(session, sku):
    session.add(Product(sku=sku, name="Bad", unit="Cuộn"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_a_product_without_an_allocated_sku_cannot_be_stored(session):
    session.add(Product(name="No SKU", unit="Cuộn"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_concurrent_creations_get_distinct_contiguous_skus(session):
    factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)

    def create(index: int) -> str:
        with factory() as own_session:
            return _create(own_session, f"Concurrent {index}").sku

    with ThreadPoolExecutor(max_workers=6) as pool:
        skus = list(pool.map(create, range(24)))

    assert sorted(skus) == [f"UG{n:06d}" for n in range(1, 25)]
    assert session.scalar(select(ProductSkuSequence.last_number)) == 24


def test_an_exhausted_sequence_fails_instead_of_wrapping(session):
    session.get(ProductSkuSequence, 1).last_number = catalog.SKU_MAX_NUMBER
    session.commit()

    with pytest.raises(catalog.CatalogConflict) as raised:
        catalog.allocate_sku(session)
    assert raised.value.code == "SKU_SEQUENCE_EXHAUSTED"


# Lifecycle -------------------------------------------------------------------


def test_a_caller_cannot_choose_or_change_a_sku():
    with pytest.raises(ValidationError):
        ProductCreate(name="Chosen", unit="Cuộn", sku="UG000777")
    with pytest.raises(ValidationError):
        ProductUpdate(sku="UG000777")


def test_update_changes_description_and_discontinues_but_keeps_identity(session):
    product = _create(session, code="TP.KT175")
    original_id, original_sku = product.id, product.sku

    updated = catalog.update_product(
        session,
        product.id,
        ProductUpdate(name="Khăn giấy lau tay 175gr", status="discontinued"),
    )

    assert updated.id == original_id
    assert updated.sku == original_sku
    assert updated.code == "TP.KT175"
    assert updated.status == "discontinued"
    assert catalog.list_products(session, status="active") == []
    assert [p.sku for p in catalog.list_products(session, status="discontinued")] == [original_sku]


def test_an_unknown_status_is_rejected():
    with pytest.raises(ValidationError):
        ProductCreate(name="X", unit="Cuộn", status="retired")


def test_updating_a_missing_product_is_not_found(session):
    with pytest.raises(catalog.CatalogNotFound):
        catalog.update_product(session, "missing", ProductUpdate(name="X"))


# EasyBooks mapping --------------------------------------------------------------


def test_easybooks_sync_allocates_skus_and_a_resync_preserves_identity(session, fixture_bundle):
    def identities():
        return {
            p.code: (p.id, p.sku, p.easybooks_material_goods_id)
            for p in session.scalars(select(Product))
        }

    sync_bundle(session, fixture_bundle)
    first = identities()
    sync_bundle(session, fixture_bundle)
    second = identities()

    assert sorted(sku for _, sku, _ in first.values()) == ["UG000001", "UG000002"]
    assert second == first


def test_a_product_created_in_uniops_keeps_its_sku_when_easybooks_later_matches_it(session):
    product = _create(session, "Towel (UniOps name)", code="TP.KT175")

    _catalog_product(
        session,
        CatalogItem(source_id="eb-175", code="TP.KT175", name="Khăn giấy 175gr", unit="Gói"),
    )
    session.commit()

    matched = session.scalar(select(Product).where(Product.code == "TP.KT175"))
    assert matched.id == product.id
    assert matched.sku == "UG000001"
    assert matched.easybooks_material_goods_id == "eb-175"
    assert session.scalar(select(ProductSkuSequence.last_number)) == 1


# API and access ------------------------------------------------------------------


def test_api_lifecycle(client):
    created = client.post(
        "/api/products",
        json={
            "name": "API Towel",
            "unit": "Roll",
            "category": "hand-towel",
            "specifications": {"gsm": 22},
            "code": "TP.KT200",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["sku"] == "UG000001"
    assert body["code"] == "TP.KT200"
    assert body["status"] == "active"

    assert client.get(f"/api/products/{body['id']}").json()["sku"] == "UG000001"
    assert client.get("/api/products?search=UG000001").json()[0]["id"] == body["id"]
    assert client.get("/api/products?category=hand-towel").json()[0]["id"] == body["id"]

    patched = client.patch(f"/api/products/{body['id']}", json={"status": "discontinued"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["sku"] == "UG000001"
    assert client.get("/api/products?status=active").json() == []

    assert client.get("/api/products/nope").status_code == 404


def test_api_refuses_a_sku_on_create_and_update(client):
    assert client.post(
        "/api/products", json={"name": "X", "unit": "Cuộn", "sku": "UG000777"}
    ).status_code == 422
    product_id = client.post("/api/products", json={"name": "X", "unit": "Cuộn"}).json()["id"]
    assert client.patch(f"/api/products/{product_id}", json={"sku": "UG000777"}).status_code == 422
    assert client.get("/api/products?status=retired").status_code == 422


def test_roles_on_canonical_product_routes(factory_client, office_client, anonymous_client):
    assert anonymous_client.get("/api/products").status_code == 401
    assert factory_client.get("/api/products").status_code == 200
    payload = {"name": "X", "unit": "Cuộn"}
    assert factory_client.post("/api/products", json=payload).status_code == 403
    assert office_client.post("/api/products", json=payload).status_code == 201


def test_the_catalogue_service_key_opens_only_product_read_and_create(
    anonymous_client, monkeypatch
):
    monkeypatch.setattr(get_settings(), "catalog_service_key", SecretStr(SERVICE_KEY))
    key = {"X-UniOps-Catalog-Key": SERVICE_KEY}

    assert anonymous_client.get("/api/products", headers=key).status_code == 200
    created = anonymous_client.post(
        "/api/products", headers=key, json={"name": "From catalogue", "unit": "Gói"}
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]
    assert anonymous_client.get(f"/api/products/{product_id}", headers=key).status_code == 200

    # The key is not a user: it cannot edit a canonical product or reach anything else.
    assert anonymous_client.patch(
        f"/api/products/{product_id}", headers=key, json={"name": "Renamed"}
    ).status_code == 401
    assert anonymous_client.get("/api/orders", headers=key).status_code == 401
    assert anonymous_client.get("/api/customers", headers=key).status_code == 401


def test_a_wrong_or_unconfigured_service_key_is_refused_with_a_clear_code(
    anonymous_client, monkeypatch
):
    wrong = {"X-UniOps-Catalog-Key": "w" * 40}

    unconfigured = anonymous_client.get("/api/products", headers=wrong)
    assert unconfigured.status_code == 401
    assert unconfigured.json()["code"] == "CATALOG_SERVICE_KEY_INVALID"

    monkeypatch.setattr(get_settings(), "catalog_service_key", SecretStr(SERVICE_KEY))
    refused = anonymous_client.get("/api/products", headers=wrong)
    assert refused.status_code == 401
    assert refused.json()["code"] == "CATALOG_SERVICE_KEY_INVALID"


def test_a_short_service_key_is_refused_at_startup():
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(catalog_service_key="short")
    assert Settings(catalog_service_key="").catalog_service_key is None
