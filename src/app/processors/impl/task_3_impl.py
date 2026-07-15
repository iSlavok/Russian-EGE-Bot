from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.formatters import Task3Formatter
from app.processors.schemas import Task3Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits


class Task3ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 3.

    Пользователь читает фрагмент текста и 5 утверждений о нём,
    затем вводит номера верных утверждений.
    """

    _formatter = Task3Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task3Content.model_validate(exercise.content)
        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.condition(content), options=None),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError

        exercise = user.current_exercises[0]
        content = Task3Content.model_validate(exercise.content)

        is_correct = extract_sorted_digits(user_answer) == extract_sorted_digits(exercise.answer)

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        return CheckResult(
            is_correct=is_correct,
            explanation=None,
            result_view=self._formatter.result(
                content, exercise.answer, exercise.explanation or "", user_answer, is_correct=is_correct,
            ),
        )
