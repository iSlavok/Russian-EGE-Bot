"""
add user_stats tables

Revision ID: c4f2a8b91d3e
Revises: a92611f90877
Create Date: 2026-04-04 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4f2a8b91d3e"
down_revision: str | Sequence[str] | None = "a92611f90877"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("total_answered", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_correct", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_daily_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_daily_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_answer_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_stats_user_id"),
    )
    op.create_index(op.f("ix_user_stats_id"), "user_stats", ["id"])

    op.create_table(
        "user_category_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("total_answered", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_correct", sa.Integer(), server_default="0", nullable=False),
        sa.Column("distinct_answered", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "category_id", name="uq_user_category_stats_user_category"),
    )
    op.create_index(op.f("ix_user_category_stats_id"), "user_category_stats", ["id"])

    op.add_column("categories", sa.Column("is_ege_task", sa.Boolean(), server_default="false", nullable=False))

    # Backfill user_stats from user_answers
    op.execute("""
        INSERT INTO user_stats (user_id, total_answered, total_correct, current_streak, max_streak,
                                current_daily_streak, max_daily_streak, last_answer_date)
        SELECT
            ua.user_id,
            COUNT(*),
            SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END),
            0,
            0,
            0,
            0,
            MAX(ua.created_at::date)
        FROM user_answers ua
        GROUP BY ua.user_id
    """)

    # Backfill user_category_stats from user_answers
    op.execute("""
        INSERT INTO user_category_stats (user_id, category_id, total_answered, total_correct, distinct_answered)
        SELECT
            ua.user_id,
            ua.category_id,
            COUNT(*),
            SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END),
            COUNT(DISTINCT ua.exercise_id)
        FROM user_answers ua
        GROUP BY ua.user_id, ua.category_id
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("categories", "is_ege_task")
    op.drop_index(op.f("ix_user_category_stats_id"), table_name="user_category_stats")
    op.drop_table("user_category_stats")
    op.drop_index(op.f("ix_user_stats_id"), table_name="user_stats")
    op.drop_table("user_stats")
