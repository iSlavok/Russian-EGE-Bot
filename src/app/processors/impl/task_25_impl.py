from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task25Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import check_answer, split_html_text


class Task25ExamProcessor(BaseTaskProcessor):
    """Задание 25 — лексический анализ текста (синонимы, антонимы, фразеологизмы и т.д.)."""

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task25Content.model_validate(exercise.content)
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

        correct_options = exercise.answer.split(";")
        is_correct = any(check_answer(user_answer, opt) for opt in correct_options)

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        correct_display = exercise.answer.replace(";", " / ")

        if is_correct:
            header = f"<b>Ответ:</b> {correct_display}"
        else:
            header = (
                f"<b>Ваш ответ:</b> {user_answer}\n"
                f"<b>Правильный ответ:</b> {correct_display}"
            )

        content = Task25Content.model_validate(exercise.content)

        explanation = header
        if exercise.explanation:
            explanation += f"\n\n<b>Объяснение:</b>{exercise.explanation}"
        explanation += f"\n\n<b>Задание:</b>\n{content.task}"
        explanation += f"\n\n<b>Фрагмент:</b>\n<blockquote expandable><i>{content.sentences}</i></blockquote>"

        return CheckResult(is_correct=is_correct, explanation=explanation)
