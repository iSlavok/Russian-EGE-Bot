from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models import Exercise


class ExerciseDTO(BaseModel):
    id: int
    category_id: int
    group_id: UUID | None
    order_index: int | None
    content: dict[str, Any]
    answer: str
    explanation: str
    is_active: bool

    @classmethod
    def from_orm_obj(cls, orm_obj: Exercise) -> "ExerciseDTO":
        return cls(
            id=orm_obj.id,
            category_id=orm_obj.category_id,
            group_id=orm_obj.group_id,
            order_index=orm_obj.order_index,
            content=orm_obj.content,
            answer=orm_obj.answer,
            explanation=orm_obj.explanation,
            is_active=orm_obj.is_active,
        )
