from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models import User
from app.schemas import CategoryDTO, ExerciseDTO


class UserDTO(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    full_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    exercise_started_at: datetime | None
    current_task_config: dict[str, Any] | None = None
    current_category_id: int | None = None

    @classmethod
    def from_orm_obj(cls, orm_obj: User) -> "UserDTO":
        return cls(
            id=orm_obj.id,
            telegram_id=orm_obj.telegram_id,
            username=orm_obj.username,
            full_name=orm_obj.full_name,
            created_at=orm_obj.created_at,
            exercise_started_at=orm_obj.exercise_started_at,
            current_task_config=orm_obj.current_task_config,
            current_category_id=orm_obj.current_category_id,
        )


class UserWithCategoryDTO(UserDTO):
    current_category: CategoryDTO | None = None

    @classmethod
    def from_orm_obj(cls, orm_obj: User, *, load_category: bool = True) -> "UserWithCategoryDTO":
        user_dto = UserDTO.from_orm_obj(orm_obj)
        current_category_dto = None

        if load_category and orm_obj.current_category:
            current_category_dto = CategoryDTO.from_orm_obj(orm_obj.current_category)

        return cls(
            **user_dto.model_dump(),
            current_category=current_category_dto,
        )


class UserWithExercisesDTO(UserWithCategoryDTO):
    current_exercises: list[ExerciseDTO] | None = None

    @classmethod
    def from_orm_obj(
            cls,
            orm_obj: User,
            *, load_exercises: bool = True,
            load_category: bool = True,
    ) -> "UserWithExercisesDTO":
        user_dto = UserWithCategoryDTO.from_orm_obj(orm_obj, load_category=load_category)
        current_exercises_dto = None

        if load_exercises and orm_obj.current_exercises:
            current_exercises_dto = [
                ExerciseDTO.from_orm_obj(exercise) for exercise in orm_obj.current_exercises
            ]

        return cls(
            **user_dto.model_dump(),
            current_exercises=current_exercises_dto,
        )
