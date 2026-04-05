from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import BaseDBModel


class UserCategoryStat(BaseDBModel):
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    total_answered: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    total_correct: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    distinct_answered: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_user_category_stats_user_category"),
    )

    def __repr__(self) -> str:
        return f"<UserCategoryStat user={self.user_id} cat={self.category_id} answered={self.total_answered}>"
