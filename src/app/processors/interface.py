from typing import Protocol

from app.schemas import CheckResult, TaskResponse, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO


class TaskProcessor(Protocol):
    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse: ...

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult: ...
