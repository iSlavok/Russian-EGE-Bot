from app.processors import BaseTaskProcessor
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO


class SkipProcessor(BaseTaskProcessor):
    """Процессор для пропуска заданий."""

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        return TaskResponse(
            task_ui=TaskUI(
                text="Это скипаем",
                options=None,
            ),
            exercise_ids=[],
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        return CheckResult(
            is_correct=True,
            explanation="Скип",
        )


class SoonProcessor(BaseTaskProcessor):
    """Процессор для заданий в разработке."""

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        return TaskResponse(
            task_ui=TaskUI(
                text="Скоро появится",
                options=None,
            ),
            exercise_ids=[],
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        return CheckResult(
            is_correct=True,
            explanation="В разработке",
        )
