from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task26Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import split_html_text


class Task26ExamProcessor(BaseTaskProcessor):
    """Задание 26 — средства связи предложений в тексте."""

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

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
            msg = "User has no current exercises"
            raise ValueError(msg)
        exercise = user.current_exercises[0]

        user_clean = "".join(c for c in user_answer if c.isdigit())
        is_correct = user_clean == exercise.answer

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        self._answer_repository.add(UserAnswer(
            is_correct=is_correct,
            user_response=user_answer,
            solve_time=solve_time,
            user_id=user.id,
            exercise_id=exercise.id,
            category_id=user.current_category_id,
        ))

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
