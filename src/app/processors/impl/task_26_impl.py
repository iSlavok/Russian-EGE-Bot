from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.formatters import Task26Formatter
from app.processors.schemas import Task26Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_digits


class Task26ExamProcessor(BaseTaskProcessor):
    """Задание 26 — средства связи предложений в тексте."""

    _formatter = Task26Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task26Content.model_validate(exercise.content)
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

        user_clean = extract_digits(user_answer)
        is_correct = user_clean == exercise.answer

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task26Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            explanation=None,
            result_view=self._formatter.result(
                correct_answer=exercise.answer,
                user_answer=user_clean,
                sentences=content.sentences,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )
