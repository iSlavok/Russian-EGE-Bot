import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import BaseDBModel

if TYPE_CHECKING:
    from app.models import Category, UserAnswer


class Exercise(BaseDBModel):
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)

    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None, index=True)
    order_index: Mapped[int | None] = mapped_column(default=None, nullable=True)

    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    answer: Mapped[str] = mapped_column(String(100), nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["Category"] = relationship(
        "Category",
        foreign_keys=[category_id],
        back_populates="exercises",
    )
    user_answers: Mapped[list["UserAnswer"]] = relationship(
        "UserAnswer",
        back_populates="exercise",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Exercise {self.id} (Cat: {self.category_id})>"
