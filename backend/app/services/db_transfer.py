"""Copy a whole UniOps database into another one.

This exists for the one-way move from the v0.1 SQLite file to the PostgreSQL
deployment target. It is a full copy, not a merge: the destination must already
be migrated to the same Alembic revision and every table it holds must be empty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Engine, create_engine, func, inspect, select, text

from app.database import Base
from app.security import as_utc


class TransferRefused(Exception):
    """A precondition failed, so nothing was copied."""


@dataclass
class TransferSummary:
    rows_by_table: dict[str, int] = field(default_factory=dict)

    @property
    def total_rows(self) -> int:
        return sum(self.rows_by_table.values())


def _alembic_revision(engine: Engine) -> str | None:
    if not inspect(engine).has_table("alembic_version"):
        return None
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


def _normalize(row: dict) -> dict:
    """Restore UTC on timestamps that lost it in storage.

    SQLite has no timezone type and returns a naive datetime for a column the
    application wrote as aware UTC. Inserting that naive value into a
    PostgreSQL `timestamptz` would have the server read it in its own timezone
    and shift every timestamp silently.
    """
    return {
        key: as_utc(value) if isinstance(value, datetime) else value for key, value in row.items()
    }


def transfer(source_url: str, target_url: str, *, batch_size: int = 1000) -> TransferSummary:
    source = create_engine(source_url)
    target = create_engine(target_url)
    try:
        return _transfer(source, target, batch_size)
    finally:
        source.dispose()
        target.dispose()


def _transfer(source: Engine, target: Engine, batch_size: int) -> TransferSummary:
    source_revision = _alembic_revision(source)
    target_revision = _alembic_revision(target)
    if source_revision is None:
        raise TransferRefused("the source database has no alembic_version table")
    if target_revision is None:
        raise TransferRefused(
            "the target database has no alembic_version table; run `alembic upgrade head` "
            "against it first"
        )
    if source_revision != target_revision:
        raise TransferRefused(
            f"schema mismatch: source is at {source_revision}, target at {target_revision}. "
            "Bring both to the same revision before copying."
        )

    tables = list(Base.metadata.sorted_tables)
    target_inspector = inspect(target)
    with target.connect() as connection:
        for table in tables:
            if not target_inspector.has_table(table.name):
                raise TransferRefused(f"the target database is missing the {table.name} table")
            existing = connection.scalar(select(func.count()).select_from(table))
            if existing:
                raise TransferRefused(
                    f"the target {table.name} table already holds {existing} rows; "
                    "this command only fills an empty database"
                )

    summary = TransferSummary()
    # Copying and verifying share one transaction, so a count that does not
    # reconcile leaves the target empty instead of half filled.
    with source.connect() as reader, target.begin() as writer:
        for table in tables:
            copied = 0
            result = reader.execution_options(stream_results=True).execute(select(table))
            while batch := result.mappings().fetchmany(batch_size):
                writer.execute(table.insert(), [_normalize(dict(row)) for row in batch])
                copied += len(batch)
            summary.rows_by_table[table.name] = copied

        for table in tables:
            expected = reader.scalar(select(func.count()).select_from(table))
            actual = writer.scalar(select(func.count()).select_from(table))
            if expected != actual:
                raise TransferRefused(
                    f"{table.name} copied {actual} rows but the source holds {expected}"
                )
    return summary
