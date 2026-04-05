from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import BaseDBModel


class UserStat(BaseDBModel):
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_answered: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    total_correct: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    max_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    current_daily_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    max_daily_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    last_answer_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_stats_user_id"),
    )

    def __repr__(self) -> str:
        return f"<UserStat user_id={self.user_id} answered={self.total_answered}>"
