from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

from .formatter import Task2Formatter
from .schemas import Task2Content


class Task2DrillProcessor(BaseTaskProcessor):
    """Процессор для тренировочного режима задания 2.

    Пользователь должен определить, соответствует ли указанное лексическое значение
    слова его значению в данном контексте.
    """

    _formatter = Task2Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task2Content.model_validate(exercise.content)
        options = [
            TaskOption(text="Подходит", value="true"),
            TaskOption(text="Не подходит", value="false"),
        ]
        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.condition(content), options=options),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        is_correct = await self._process_answer_single_exercise(user, user_answer)

        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        content = Task2Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.result(
                content, exercise.answer, exercise.explanation, is_correct=is_correct,
            ),
        )
