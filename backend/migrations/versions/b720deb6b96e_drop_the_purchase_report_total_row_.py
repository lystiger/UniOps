"""drop the purchase report total row mistaken for a document

The EasyBooks `mua-hang` report ends with a grand-total line whose money fields
hold the sum of every row above it. It carries no document identity: no refID,
no document or invoice date, no vendor, no type. Only a display label, observed
as `soCTu = "Tong cong"`.

UniOps normalized it as a purchase document. The same money was therefore
counted twice - once across the real documents and once in the footer - and an
all-time purchase total came out at exactly double the truth. In the production
database that is one document carrying 3,434,358,898 against 54 real ones
summing to the same figure.

The connector now recognises and skips such rows, and reports how many it
skipped. This migration removes the ones already stored.

Only the derived rows are deleted. Every raw payload is kept untouched, which is
the point of an append-only raw layer: our reading of the source changed, the
source did not. The footer row is still there in
`easybooks_raw_records` for anyone who wants to see what was misread.

A downgrade does not put the derived rows back. It cannot know which reading of
the source to restore, and the raw payloads make the fact recoverable anyway.

Revision ID: b720deb6b96e
Revises: 3013e9039073
Create Date: 2026-09-09 15:10:44.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b720deb6b96e'
down_revision: Union[str, Sequence[str], None] = '3013e9039073'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The normalized fingerprint of a row that had no document identity at all.
# `fallback:` means the key had to be derived because no refID was present.
_TOTAL_ROW_DOCUMENTS = """
    SELECT id FROM purchase_documents
    WHERE document_date IS NULL
      AND vendor_code IS NULL
      AND source_type IS NULL
      AND invoice_number IS NULL
      AND source_id LIKE 'fallback:%'
"""


def upgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM purchase_lines WHERE purchase_document_id IN "
            f"({_TOTAL_ROW_DOCUMENTS})"
        )
    )
    op.execute(sa.text(f"DELETE FROM purchase_documents WHERE id IN ({_TOTAL_ROW_DOCUMENTS})"))


def downgrade() -> None:
    """Nothing to restore. The raw payloads were never removed."""
