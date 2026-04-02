from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task26Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_digits, split_html_text


class Task26ExamProcessor(BaseTaskProcessor):
    """Задание 26 — средства связи предложений в тексте."""

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_random_exercise(category.id, user.id)

        content = Task26Content.model_validate(exercise.content)
        task_text = f"{content.task}\n\n<i>{content.sentences}</i>"

        parts = split_html_text(task_text)
        continuation = parts[1] if len(parts) == 2 else None  # noqa: PLR2004

        return TaskResponse(
            task_ui=TaskUI(text=parts[0], text_continuation=continuation, options=None),
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

        if is_correct:
            header = f"<b>Ответ:</b> {exercise.answer}"
        else:
            header = (
                f"<b>Ваш ответ:</b> {user_clean or '—'}\n"
                f"<b>Правильный ответ:</b> {exercise.answer}"
            )

        content = Task26Content.model_validate(exercise.content)

        explanation = header
        if exercise.explanation:
            explanation += f"\n\n<b>Объяснение:</b> {exercise.explanation}"
        explanation += f"\n\n<b>Задание:</b>\n{content.task}"
        explanation += f"\n\n<b>Фрагмент:</b>\n<blockquote expandable><i>{content.sentences}</i></blockquote>"

        return CheckResult(is_correct=is_correct, explanation=explanation)
