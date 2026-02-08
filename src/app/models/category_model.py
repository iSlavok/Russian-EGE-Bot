from typing import TYPE_CHECKING

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import BaseDBModel
from app.enums import HandlerType

if TYPE_CHECKING:
    from app.models import Exercise, UserAnswer


class Category(BaseDBModel):
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    handler_type: Mapped[HandlerType] = mapped_column(
        SqlEnum(HandlerType, name="handler_type_enum", native_enum=False, length=32),
        nullable=True,
        default=None,
    )

    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True, nullable=True)

    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan",
        primaryjoin="Category.parent_id == Category.id",
        foreign_keys="[Category.parent_id]",
        order_by="Category.id.asc()",
    )
    parent: Mapped["Category | None"] = relationship(
        "Category",
        back_populates="children",
        primaryjoin="Category.parent_id == Category.id",
        foreign_keys="[Category.parent_id]",
        remote_side="[Category.id]",
    )

    exercises: Mapped[list["Exercise"]] = relationship(
        "Exercise",
        back_populates="category",
        cascade="all, delete-orphan",
    )
    user_answers: Mapped[list["UserAnswer"]] = relationship(
        "UserAnswer",
        back_populates="category",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Category {self.name} (ID: {self.id})>"
