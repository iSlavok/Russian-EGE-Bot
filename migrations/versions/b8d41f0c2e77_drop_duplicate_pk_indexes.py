"""
drop indexes duplicating the primary key

Revision ID: b8d41f0c2e77
Revises: c4f2a8b91d3e
Create Date: 2026-10-01 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = "b8d41f0c2e77"
down_revision: str | Sequence[str] | None = "c4f2a8b91d3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "categories",
    "exercises",
    "user_answers",
    "user_category_stats",
    "user_stats",
    "users",
)


def upgrade() -> None:
    """Upgrade schema."""
    for table in _TABLES:
        op.drop_index(op.f(f"ix_{table}_id"), table_name=table)


def downgrade() -> None:
    """Downgrade schema."""
    for table in reversed(_TABLES):
        op.create_index(op.f(f"ix_{table}_id"), table, ["id"], unique=False)
