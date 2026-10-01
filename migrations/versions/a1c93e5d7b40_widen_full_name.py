"""
widen users.full_name to Telegram's actual limit

Revision ID: a1c93e5d7b40
Revises: b8d41f0c2e77
Create Date: 2026-10-02 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c93e5d7b40"
down_revision: str | Sequence[str] | None = "b8d41f0c2e77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "users",
        "full_name",
        existing_type=sa.String(length=64),
        type_=sa.String(length=129),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE users SET full_name = left(full_name, 64) WHERE length(full_name) > 64")
    op.alter_column(
        "users",
        "full_name",
        existing_type=sa.String(length=129),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
