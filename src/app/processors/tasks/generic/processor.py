from app.processors import BaseTaskProcessor
from app.schemas import CheckResult, ResultView, TaskResponse, TaskUI, TaskView, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO


class SkipProcessor(BaseTaskProcessor):
    """Процессор для пропуска заданий."""

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        return TaskResponse(
            task_ui=TaskUI(view=TaskView(heading="Пропуск", instruction="Это задание пропускается.")),
            exercise_ids=[],
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        return CheckResult(is_correct=True, result_view=ResultView(correct=True))


class SoonProcessor(BaseTaskProcessor):
    """Процессор для заданий в разработке."""

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        return TaskResponse(
            task_ui=TaskUI(view=TaskView(heading="В разработке", instruction="Это задание скоро появится.")),
            exercise_ids=[],
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        return CheckResult(is_correct=True, result_view=ResultView(correct=True))
