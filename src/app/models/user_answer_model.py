from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import BaseDBModel

if TYPE_CHECKING:
    from app.models import Category, Exercise, User


class UserAnswer(BaseDBModel):
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    user_response: Mapped[str] = mapped_column(String(256), nullable=False)
    solve_time: Mapped[int] = mapped_column(Integer, nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True, nullable=False)

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="answers",
    )
    exercise: Mapped["Exercise"] = relationship(
        "Exercise",
        foreign_keys=[exercise_id],
        back_populates="user_answers",
    )
    category: Mapped["Category"] = relationship(
        "Category",
        foreign_keys=[category_id],
        back_populates="user_answers",
    )

    __table_args__ = (
        Index("ix_user_answers_user_id_created_at", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Answer User:{self.user_id} Task:{self.exercise_id} Correct:{self.is_correct}>"
