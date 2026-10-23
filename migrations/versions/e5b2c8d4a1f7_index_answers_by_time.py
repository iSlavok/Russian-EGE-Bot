"""
index answers by time

Revision ID: e5b2c8d4a1f7
Revises: d3e7f1a9c2b4
Create Date: 2026-10-24 13:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = "e5b2c8d4a1f7"
down_revision: str | Sequence[str] | None = "d3e7f1a9c2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_user_answers_created_at", "user_answers", ["created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_user_answers_created_at", table_name="user_answers")
