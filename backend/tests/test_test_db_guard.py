import pytest
from conftest import validate_test_database_url


def test_guard_allows_none():
    validate_test_database_url(None, None)
    validate_test_database_url(None, "postgresql+psycopg://uniops:pass@127.0.0.1:5432/uniops")


def test_guard_allows_valid_test_db():
    validate_test_database_url(
        "postgresql+psycopg://uniops:pass@127.0.0.1:5432/uniops_test",
        "postgresql+psycopg://uniops:pass@127.0.0.1:5432/uniops",
    )


def test_guard_refuses_matching_normal_db():
    with pytest.raises(pytest.UsageError, match="matches UNIOPS_DATABASE_URL"):
        validate_test_database_url(
            "postgresql+psycopg://uniops:pass@127.0.0.1:5432/uniops_test",
            "postgresql+psycopg://uniops:pass@127.0.0.1:5432/uniops_test",
        )


def test_guard_refuses_dev_or_prod_database_names():
    for dangerous in ["uniops", "postgres", "production", "prod", "mydb"]:
        with pytest.raises(pytest.UsageError, match="dedicated test database"):
            validate_test_database_url(
                f"postgresql+psycopg://uniops:pass@127.0.0.1:5432/{dangerous}",
                None,
            )
