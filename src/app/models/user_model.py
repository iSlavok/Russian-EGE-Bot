from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import BaseDBModel

if TYPE_CHECKING:
    from app.models import Category, Exercise, UserAnswer


TG_USERNAME_MAX_LEN = 32
TG_NAME_PART_MAX_LEN = 64
TG_FULL_NAME_MAX_LEN = TG_NAME_PART_MAX_LEN * 2 + 1


user_current_exercises = Table(
    "user_current_exercises",
    BaseDBModel.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("exercise_id", ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True),
)


class User(BaseDBModel):
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(TG_USERNAME_MAX_LEN), nullable=True)
    full_name: Mapped[str] = mapped_column(String(TG_FULL_NAME_MAX_LEN), nullable=False)

    exercise_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_task_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    current_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True, nullable=True)

    current_exercises: Mapped[list["Exercise"]] = relationship(
        "Exercise",
        secondary=user_current_exercises,
    )
    current_category: Mapped["Category | None"] = relationship(
        "Category",
        foreign_keys=[current_category_id],
    )
    answers: Mapped[list["UserAnswer"]] = relationship(
        "UserAnswer",
        back_populates="user",
        cascade="all, delete-orphan",
    )


    def __repr__(self) -> str:
        return f"<User {self.id}, telegram_id={self.telegram_id}, username={self.username}>"
