"""purchase line vat is an amount not a rate

`thueGTGT` on the EasyBooks purchase report carries the VAT in dong, not a
percentage. The column was created as NUMERIC(8,4), which SQLite accepts
regardless of precision and PostgreSQL refuses with "numeric field overflow" on
any real invoice. The stored numbers were always amounts, so this renames and
rescales the column in place rather than dropping it.

Revision ID: 5dcbe229a253
Revises: 9166882e1199
Create Date: 2026-09-09 14:41:08.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5dcbe229a253'
down_revision: Union[str, Sequence[str], None] = '9166882e1199'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('purchase_lines', schema=None) as batch_op:
        batch_op.alter_column(
            'vat_rate',
            new_column_name='vat_amount',
            existing_type=sa.Numeric(precision=8, scale=4),
            type_=sa.Numeric(precision=18, scale=2),
            existing_nullable=True,
        )


def downgrade() -> None:
    # Reversing the scale truncates any amount above 9999.9999, which is every
    # real row. The column is restored, the values in it are not.
    with op.batch_alter_table('purchase_lines', schema=None) as batch_op:
        batch_op.alter_column(
            'vat_amount',
            new_column_name='vat_rate',
            existing_type=sa.Numeric(precision=18, scale=2),
            type_=sa.Numeric(precision=8, scale=4),
            existing_nullable=True,
        )
