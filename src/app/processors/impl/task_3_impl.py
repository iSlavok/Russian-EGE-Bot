import html
from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task3Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

INSTRUCTION = (
    "Укажите варианты ответов, в которых даны верные характеристики фрагмента текста. "
    "Запишите номера ответов."
)


def _normalize_digits(answer: str) -> str:
    """Извлекает цифры из строки и возвращает их в отсортированном виде."""
    return "".join(sorted(c for c in answer if c.isdigit()))


class Task3ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 3.

    Пользователь читает фрагмент текста и 5 утверждений о нём,
    затем вводит номера верных утверждений.
    """

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
        content = Task3Content.model_validate(exercise.content)

        statements_text = "\n".join(
            f"<b>{i + 1})</b> <i>{stmt}</i>" for i, stmt in enumerate(content.statements)
        )

        task_text = (
            f"{INSTRUCTION}\n\n"
            f"<b>Текст:</b>\n"
            f"<blockquote expandable>{html.escape(content.text, quote=False)}</blockquote>\n\n"
            f"{statements_text}"
        )

        return TaskResponse(
            task_ui=TaskUI(
                text=task_text,
                options=None,
            ),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises to check answer for"
            raise ValueError(msg)

        exercise = user.current_exercises[0]
        content = Task3Content.model_validate(exercise.content)

        is_correct = _normalize_digits(user_answer) == _normalize_digits(exercise.answer)

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        answer = UserAnswer(
            is_correct=is_correct,
            user_response=user_answer,
            solve_time=solve_time,
            user_id=user.id,
            exercise_id=exercise.id,
            category_id=user.current_category_id,
        )
        self._answer_repository.add(answer)

        correct = exercise.answer
        explanation = html.escape(exercise.explanation, quote=False)
        explanation = (
            f"<b>Текст:</b>\n"
            f"<blockquote expandable>{html.escape(content.text, quote=False)}</blockquote>\n\n"
            f"{explanation}"
        )

        if is_correct:
            explanation = f"<b>Ответ:</b> {correct}\n\n" + explanation
        else:
            explanation = (
                f"<b>Ваш ответ:</b> {html.escape(user_answer, quote=False)}\n"
                f"<b>Правильный ответ:</b> {correct}\n\n"
                + explanation
            )

        return CheckResult(
            is_correct=is_correct,
            explanation=explanation,
        )
