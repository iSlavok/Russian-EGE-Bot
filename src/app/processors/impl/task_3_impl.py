import html
from typing import cast

from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task3Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits

INSTRUCTION = (
    "Укажите варианты ответов, в которых даны верные характеристики фрагмента текста. "
    "Запишите номера ответов."
)


class Task3ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 3.

    Пользователь читает фрагмент текста и 5 утверждений о нём,
    затем вводит номера верных утверждений.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_random_exercise(category.id, user.id)

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
            raise NoCurrentExercisesError

        exercise = user.current_exercises[0]
        content = Task3Content.model_validate(exercise.content)

        is_correct = extract_sorted_digits(user_answer) == extract_sorted_digits(exercise.answer)

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        correct = exercise.answer
        explanation = cast("str", exercise.explanation)
        explanation = html.escape(explanation, quote=False)
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
