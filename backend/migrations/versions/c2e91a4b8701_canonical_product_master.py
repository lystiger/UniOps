"""canonical product master

Makes `products` the canonical product record:
- sku: sequential non-semantic identifier (UG000001), unique and immutable
- category, status (active / discontinued), specifications (structured JSON)

Creates product_sku_sequence, the single counter SKUs are allocated from, and
backfills existing products with SKUs in creation order.

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
    op.create_table(
        'product_sku_sequence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('last_number', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sku', sa.String(length=8), nullable=True))
        batch_op.add_column(
            sa.Column('category', sa.String(length=100), nullable=False, server_default='general')
        )
        batch_op.add_column(
            sa.Column('status', sa.String(length=20), nullable=False, server_default='active')
        )
        batch_op.add_column(
            sa.Column('specifications', sa.JSON(), nullable=False, server_default='{}')
        )

    # Existing products get SKUs in the order they were created. The numbers say
    # nothing about the product; the order only makes the backfill repeatable.
    conn = op.get_bind()
    products = sa.table(
        'products',
        sa.column('id', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('sku', sa.String),
    )
    ids = conn.execute(
        sa.select(products.c.id).order_by(products.c.created_at.asc(), products.c.id.asc())
    ).scalars().all()
    for number, product_id in enumerate(ids, start=1):
        conn.execute(
            products.update().where(products.c.id == product_id).values(sku=f"UG{number:06d}")
        )

    sequence = sa.table(
        'product_sku_sequence', sa.column('id', sa.Integer), sa.column('last_number', sa.Integer)
    )
    conn.execute(sequence.insert().values(id=1, last_number=len(ids)))

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.alter_column('sku', existing_type=sa.String(length=8), nullable=False)
        batch_op.create_unique_constraint('uq_product_sku', ['sku'])
        batch_op.create_check_constraint(
            'ck_products_sku_format', "length(sku) = 8 AND substr(sku, 1, 2) = 'UG'"
        )
        batch_op.create_check_constraint(
            'ck_products_status', "status IN ('active', 'discontinued')"
        )
        batch_op.create_index('ix_products_category', ['category'], unique=False)
        batch_op.create_index('ix_products_status', ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_index('ix_products_status')
        batch_op.drop_index('ix_products_category')
        batch_op.drop_constraint('ck_products_status', type_='check')
        batch_op.drop_constraint('ck_products_sku_format', type_='check')
        batch_op.drop_constraint('uq_product_sku', type_='unique')
        batch_op.drop_column('specifications')
        batch_op.drop_column('status')
        batch_op.drop_column('category')
        batch_op.drop_column('sku')

    op.drop_table('product_sku_sequence')
