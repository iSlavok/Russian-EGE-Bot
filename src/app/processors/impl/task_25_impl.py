from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.formatters import Task25Formatter
from app.processors.schemas import Task25Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import check_answer


class Task25ExamProcessor(BaseTaskProcessor):
    """Задание 25 — лексический анализ текста (синонимы, антонимы, фразеологизмы и т.д.)."""

    _formatter = Task25Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task25Content.model_validate(exercise.content)
        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.condition(task=content.task, sentences=content.sentences),
                options=None,
            ),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        correct_options = exercise.answer.split(";")
        is_correct = any(check_answer(user_answer, opt) for opt in correct_options)

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task25Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            explanation=None,
            result_view=self._formatter.result(
                forms=correct_options,
                user_answer=user_answer,
                sentences=content.sentences,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )
