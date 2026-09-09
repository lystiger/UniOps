"""The one-way copy from the v0.1 SQLite file to the PostgreSQL target."""

from datetime import UTC, datetime

import pytest
from app.database import Base
from app.models import Customer, Order, OrderLine, UserRole
from app.services import auth
from app.services.db_transfer import TransferRefused, _normalize, transfer
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

REVISION = "9166882e1199"


def _build(path, revision=REVISION):
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
        connection.execute(
            text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": revision}
        )
    return engine


def _fill(engine):
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        auth.create_user(
            session, username="office", password="office-password-01", role=UserRole.OFFICE
        )
        customer = Customer(name="Fixture Customer", tax_code="0100000000")
        session.add(customer)
        session.flush()
        order = Order(
            order_number="UO-20260909-AAA111",
            customer_id=customer.id,
            order_date=datetime(2026, 9, 9).date(),
            required_date=datetime(2026, 9, 12).date(),
        )
        session.add(order)
        session.flush()
        session.add(
            OrderLine(
                order_id=order.id,
                position=1,
                description="Paper roll",
                quantity="10.0000",
                unit="roll",
            )
        )
        session.commit()


def test_a_full_copy_lands_every_row(tmp_path):
    source = _build(tmp_path / "source.db")
    _fill(source)
    _build(tmp_path / "target.db")

    summary = transfer(f"sqlite:///{tmp_path / 'source.db'}", f"sqlite:///{tmp_path / 'target.db'}")

    assert summary.rows_by_table["customers"] == 1
    assert summary.rows_by_table["orders"] == 1
    assert summary.rows_by_table["order_lines"] == 1
    assert summary.rows_by_table["users"] == 1

    target = create_engine(f"sqlite:///{tmp_path / 'target.db'}")
    with sessionmaker(bind=target)() as session:
        copied = session.query(Order).one()
        assert copied.order_number == "UO-20260909-AAA111"
        assert copied.customer.name == "Fixture Customer"
    source.dispose()
    target.dispose()


def test_a_revision_mismatch_is_refused_before_anything_is_copied(tmp_path):
    _build(tmp_path / "source.db")
    _build(tmp_path / "target.db", revision="9e47c86f437b")

    with pytest.raises(TransferRefused, match="schema mismatch"):
        transfer(f"sqlite:///{tmp_path / 'source.db'}", f"sqlite:///{tmp_path / 'target.db'}")


def test_a_target_holding_rows_is_refused(tmp_path):
    source = _build(tmp_path / "source.db")
    _fill(source)
    target = _build(tmp_path / "target.db")
    _fill(target)

    with pytest.raises(TransferRefused, match="already holds"):
        transfer(f"sqlite:///{tmp_path / 'source.db'}", f"sqlite:///{tmp_path / 'target.db'}")
    source.dispose()
    target.dispose()


def test_an_unmigrated_target_is_named_as_the_problem(tmp_path):
    _build(tmp_path / "source.db")
    create_engine(f"sqlite:///{tmp_path / 'target.db'}").connect().close()

    with pytest.raises(TransferRefused, match="alembic upgrade head"):
        transfer(f"sqlite:///{tmp_path / 'source.db'}", f"sqlite:///{tmp_path / 'target.db'}")


def test_a_timestamp_that_lost_its_zone_is_read_back_as_utc():
    """SQLite returns naive datetimes; PostgreSQL would read those as local time."""
    naive = datetime(2026, 9, 9, 7, 30)
    assert _normalize({"created_at": naive})["created_at"] == naive.replace(tzinfo=UTC)

    aware = datetime(2026, 9, 9, 7, 30, tzinfo=UTC)
    assert _normalize({"created_at": aware})["created_at"] == aware
