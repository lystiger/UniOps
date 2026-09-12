"""canonical product master

Adds canonical product identity fields to products table:
- sku (sequential non-semantic identifier, e.g. UG000001)
- category (e.g. general)
- status (active / discontinued)
- specifications (structured JSON attributes)

Creates product_sku_sequence to ensure atomic and deterministic SKU sequence allocation.
Backfills existing products with sequential SKUs.

Revision ID: c2e91a4b8701
Revises: 7dfd34c9902d
Create Date: 2026-09-13 01:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2e91a4b8701'
down_revision: Union[str, Sequence[str], None] = '7dfd34c9902d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create product_sku_sequence
    op.create_table(
        'product_sku_sequence',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('last_number', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2. Add columns with batch_alter_table
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sku', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('category', sa.String(length=100), nullable=False, server_default='general'))
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=False, server_default='active'))
        batch_op.add_column(sa.Column('specifications', sa.JSON(), nullable=False, server_default='{}'))

    # 3. Backfill sequential SKUs for any existing products
    conn = op.get_bind()
    products_table = sa.table(
        'products',
        sa.column('id', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('sku', sa.String),
    )
    rows = conn.execute(
        sa.select(products_table.c.id).order_by(products_table.c.created_at.asc(), products_table.c.id.asc())
    ).fetchall()

    for idx, (prod_id,) in enumerate(rows, start=1):
        generated_sku = f"UG{idx:06d}"
        conn.execute(
            products_table.update().where(products_table.c.id == prod_id).values(sku=generated_sku)
        )

    # 4. Initialize the sequence
    seq_table = sa.table(
        'product_sku_sequence',
        sa.column('id', sa.Integer),
        sa.column('last_number', sa.Integer),
    )
    conn.execute(seq_table.insert().values(id=1, last_number=len(rows)))

    # 5. Enforce not null and unique constraint/indexes on sku
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.alter_column('sku', existing_type=sa.String(length=32), nullable=False)
        batch_op.create_unique_constraint('uq_product_sku', ['sku'])
        batch_op.create_index('ix_products_sku', ['sku'], unique=True)
        batch_op.create_index('ix_products_category', ['category'], unique=False)
        batch_op.create_index('ix_products_status', ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_index('ix_products_status')
        batch_op.drop_index('ix_products_category')
        batch_op.drop_index('ix_products_sku')
        batch_op.drop_constraint('uq_product_sku', type_='unique')
        batch_op.drop_column('specifications')
        batch_op.drop_column('status')
        batch_op.drop_column('category')
        batch_op.drop_column('sku')

    op.drop_table('product_sku_sequence')
