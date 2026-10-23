"""
add manual ordering and hiding of categories

Revision ID: d3e7f1a9c2b4
Revises: a1c93e5d7b40
Create Date: 2026-10-24 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e7f1a9c2b4"
down_revision: str | Sequence[str] | None = "a1c93e5d7b40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("categories", sa.Column("position", sa.Integer(), server_default="0", nullable=False))
    op.add_column("categories", sa.Column("is_hidden", sa.Boolean(), server_default="false", nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("categories", "is_hidden")
    op.drop_column("categories", "position")
