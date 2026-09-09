"""trace normalized documents to their raw source version

Adds the lineage pointers that let any normalized accounting row name the exact
immutable raw payload it came from, and the sync run that last changed it.

Before this, the only link between a normalized document and the raw layer was
`(source_system, source_id)`, which finds *every* version of that document
rather than the one that produced the row. Twelve of the fifty-five purchase
documents in the production database hold more than one raw version, so
answering "which payload produced this?" meant re-normalizing every candidate
and comparing hashes.

Existing rows are backfilled with the newest raw version held for them at
migration time. That is best effort and deliberately so: the exact version is
not recoverable from the schema as it stood. Every row touched by a sync after
this migration records its lineage exactly, and the reconciliation stage reports
any document still missing a pointer.

Revision ID: 3013e9039073
Revises: 5dcbe229a253
Create Date: 2026-09-09 14:59:21.472006
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3013e9039073'
down_revision: Union[str, Sequence[str], None] = '5dcbe229a253'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill(table: str, column: str, entity_type: str) -> None:
    """Point existing rows at the newest raw version stored for them.

    Written as a correlated subquery so it runs unchanged on SQLite and
    PostgreSQL. `retrieved_at` orders the versions; the id breaks ties so the
    result does not depend on row order.
    """
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET {column} = (
                SELECT r.id
                FROM easybooks_raw_records AS r
                WHERE r.source_system = {table}.source_system
                  AND r.entity_type = :entity_type
                  AND r.source_id = {table}.source_id
                ORDER BY r.retrieved_at DESC, r.id DESC
                LIMIT 1
            )
            """
        ).bindparams(entity_type=entity_type)
    )


def _backfill_run(table: str) -> None:
    """Attribute each row to the run that first observed its raw version."""
    op.execute(
        sa.text(
            f"""
            UPDATE {table}
            SET sync_run_id = (
                SELECT r.sync_run_id
                FROM easybooks_raw_records AS r
                WHERE r.id = {table}.source_raw_record_id
            )
            WHERE {table}.source_raw_record_id IS NOT NULL
            """
        )
    )


def upgrade() -> None:
    with op.batch_alter_table('purchase_documents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_raw_record_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('sync_run_id', sa.String(length=36), nullable=True))
        batch_op.create_index('ix_purchase_raw_lineage', ['source_raw_record_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_purchase_documents_source_raw_record',
            'easybooks_raw_records', ['source_raw_record_id'], ['id'], ondelete='RESTRICT',
        )
        batch_op.create_foreign_key(
            'fk_purchase_documents_sync_run',
            'easybooks_sync_runs', ['sync_run_id'], ['id'], ondelete='RESTRICT',
        )

    with op.batch_alter_table('sales_documents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_raw_record_id', sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column('source_lines_raw_record_id', sa.String(length=36), nullable=True)
        )
        batch_op.add_column(sa.Column('sync_run_id', sa.String(length=36), nullable=True))
        batch_op.create_index('ix_sales_raw_lineage', ['source_raw_record_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_sales_documents_source_raw_record',
            'easybooks_raw_records', ['source_raw_record_id'], ['id'], ondelete='RESTRICT',
        )
        batch_op.create_foreign_key(
            'fk_sales_documents_source_lines_raw_record',
            'easybooks_raw_records', ['source_lines_raw_record_id'], ['id'], ondelete='RESTRICT',
        )
        batch_op.create_foreign_key(
            'fk_sales_documents_sync_run',
            'easybooks_sync_runs', ['sync_run_id'], ['id'], ondelete='RESTRICT',
        )

    _backfill('sales_documents', 'source_raw_record_id', 'sales_document')
    _backfill('sales_documents', 'source_lines_raw_record_id', 'sales_lines')
    _backfill('purchase_documents', 'source_raw_record_id', 'purchase_document')
    _backfill_run('sales_documents')
    _backfill_run('purchase_documents')


def downgrade() -> None:
    """Drops the pointers only. No raw version is touched."""
    with op.batch_alter_table('sales_documents', schema=None) as batch_op:
        batch_op.drop_constraint('fk_sales_documents_sync_run', type_='foreignkey')
        batch_op.drop_constraint('fk_sales_documents_source_lines_raw_record', type_='foreignkey')
        batch_op.drop_constraint('fk_sales_documents_source_raw_record', type_='foreignkey')
        batch_op.drop_index('ix_sales_raw_lineage')
        batch_op.drop_column('sync_run_id')
        batch_op.drop_column('source_lines_raw_record_id')
        batch_op.drop_column('source_raw_record_id')

    with op.batch_alter_table('purchase_documents', schema=None) as batch_op:
        batch_op.drop_constraint('fk_purchase_documents_sync_run', type_='foreignkey')
        batch_op.drop_constraint('fk_purchase_documents_source_raw_record', type_='foreignkey')
        batch_op.drop_index('ix_purchase_raw_lineage')
        batch_op.drop_column('sync_run_id')
        batch_op.drop_column('source_raw_record_id')
