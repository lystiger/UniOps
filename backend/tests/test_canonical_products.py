from concurrent.futures import ThreadPoolExecutor

import pytest
from app.config import get_settings
from app.models import ProductStatus
from app.schemas import ProductCreate
from app.services import catalog


def test_sku_sequential_generation(session):
    # 1. Create three products without providing an explicit SKU
    p1 = catalog.create_product(
        session,
        ProductCreate(
            name="Napkin Soft 1",
            unit="Pack",
            category="napkin",
            specifications={"ply": 2, "sheet_count": 100},
        ),
    )
    p2 = catalog.create_product(
        session,
        ProductCreate(
            name="Napkin Soft 2",
            unit="Pack",
            category="napkin",
            specifications={"ply": 3, "sheet_count": 100},
        ),
    )
    p3 = catalog.create_product(
        session,
        ProductCreate(
            name="Jumbo Toilet Roll 700g",
            unit="Roll",
            category="industrial-roll",
            specifications={"weight_g": 700, "ply": 2},
        ),
    )

    assert p1.sku.startswith("UG")
    assert p2.sku.startswith("UG")
    assert p3.sku.startswith("UG")

    n1 = int(p1.sku[2:])
    n2 = int(p2.sku[2:])
    n3 = int(p3.sku[2:])

    assert n2 == n1 + 1
    assert n3 == n2 + 1
    assert p1.specifications["ply"] == 2
    assert p3.specifications["weight_g"] == 700
    assert p1.status == ProductStatus.ACTIVE.value


def test_custom_sku_and_format_validation(session):
    # Valid explicit SKU
    p = catalog.create_product(
        session,
        ProductCreate(
            sku="UG000999",
            name="Custom SKU Product",
            unit="Box",
        ),
    )
    assert p.sku == "UG000999"

    # Next auto-generated SKU should continue past 999
    next_sku = catalog.generate_next_sku(session)
    assert next_sku == "UG001000"

    # Invalid SKU format rejected
    with pytest.raises(catalog.CatalogConflict) as exc_info:
        catalog.create_product(
            session,
            ProductCreate(
                sku="INVALID-SKU",
                name="Bad SKU Product",
                unit="Box",
            ),
        )
    assert exc_info.value.code == "INVALID_SKU_FORMAT"


def test_duplicate_sku_rejected(session):
    catalog.create_product(
        session,
        ProductCreate(
            sku="UG000555",
            name="Original Product",
            unit="Box",
        ),
    )

    with pytest.raises(catalog.CatalogConflict) as exc_info:
        catalog.create_product(
            session,
            ProductCreate(
                sku="UG000555",
                name="Duplicate SKU Product",
                unit="Box",
            ),
        )
    assert exc_info.value.code == "PRODUCT_SKU_EXISTS"


def test_concurrent_sku_generation(session):
    from sqlalchemy.orm import sessionmaker

    engine = session.get_bind()
    factory = sessionmaker(bind=engine)

    with factory() as s:
        catalog.generate_next_sku(s)
        s.commit()

    def make_sku(idx: int) -> str:
        with factory() as thread_session:
            sku = catalog.generate_next_sku(thread_session)
            thread_session.commit()
            return sku

    with ThreadPoolExecutor(max_workers=4) as executor:
        skus = list(executor.map(make_sku, range(8)))

    # All generated SKUs must be unique
    assert len(skus) == len(set(skus))
    for s in skus:
        assert s.startswith("UG")
        assert len(s) == 8


def test_api_canonical_product_lifecycle(client):
    # 1. Create via API
    res = client.post(
        "/api/products",
        json={
            "name": "API Canonical Towel",
            "unit": "Roll",
            "category": "hand-towel",
            "specifications": {"gsm": 22, "core_diameter_mm": 45},
            "easybooks_code": "TP.KT200",
        },
    )
    assert res.status_code == 201
    created = res.json()
    assert created["sku"].startswith("UG")
    assert created["name"] == "API Canonical Towel"
    assert created["category"] == "hand-towel"
    assert created["specifications"]["gsm"] == 22
    assert created["easybooks_code"] == "TP.KT200"

    # 2. Get by ID
    prod_id = created["id"]
    get_res = client.get(f"/api/products/{prod_id}")
    assert get_res.status_code == 200
    assert get_res.json()["sku"] == created["sku"]

    # 3. Filter by category
    list_res = client.get("/api/products?category=hand-towel")
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(i["id"] == prod_id for i in items)

    # 4. Filter by search (SKU or name or code)
    search_res = client.get(f"/api/products?search={created['sku']}")
    assert search_res.status_code == 200
    assert any(i["id"] == prod_id for i in search_res.json())


def test_api_key_authentication(client_factory):
    settings = get_settings()
    settings.api_key = "test-internal-key-secret"

    try:
        anon = client_factory()

        # Unauthenticated request to /api/products fails 401
        unauth_res = anon.get("/api/products")
        assert unauth_res.status_code == 401

        # Request with X-UniOps-Key succeeds
        auth_res = anon.get(
            "/api/products", headers={"X-UniOps-Key": "test-internal-key-secret"}
        )
        assert auth_res.status_code == 200

        # Request with Bearer token succeeds
        bearer_res = anon.get(
            "/api/products", headers={"Authorization": "Bearer test-internal-key-secret"}
        )
        assert bearer_res.status_code == 200
    finally:
        settings.api_key = None
