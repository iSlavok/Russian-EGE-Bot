import random

from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task2324Config, Task2324Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import split_html_text

_ALL_DIGITS = frozenset("12345")


def _pick_mode(correct_digits: str) -> bool:
    """Возвращает True, если нужно спрашивать про НЕверные утверждения.

    Гарантирует не менее 2 ответов в любом режиме.
    """
    correct_count = len(set(correct_digits) & _ALL_DIGITS)
    incorrect_count = 5 - correct_count
    can_correct = correct_count >= 2  # noqa: PLR2004
    can_incorrect = incorrect_count >= 2  # noqa: PLR2004
    if can_correct and can_incorrect:
        return random.choice([True, False])
    return not can_correct


class _Task2324BaseProcessor(BaseTaskProcessor):
    _CORRECT_FORMULATION: str = ""
    _INCORRECT_FORMULATION: str = ""
    _OPTIONS_LABEL: str = ""

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_random_exercise(category.id, user.id)

        content = Task2324Content.model_validate(exercise.content)
        ask_incorrect = _pick_mode(exercise.answer)
        formulation = self._INCORRECT_FORMULATION if ask_incorrect else self._CORRECT_FORMULATION

        options_text = "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(content.options))
        task_text = (
            f"{formulation}\n\n"
            f"<b>Текст:</b>\n<blockquote expandable>{content.text}</blockquote>\n\n"
            f"{options_text}"
        )

        parts = split_html_text(task_text)
        continuation = parts[1] if len(parts) == 2 else None  # noqa: PLR2004

        return TaskResponse(
            task_ui=TaskUI(text=parts[0], text_continuation=continuation, options=None),
            exercise_ids=exercise.id,
            task_config=Task2324Config(
                correct_digits=exercise.answer,
                ask_incorrect=ask_incorrect,
            ),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        task_config = Task2324Config.model_validate(user.current_task_config)

        correct_set = set(task_config.correct_digits) & _ALL_DIGITS
        target_set = (_ALL_DIGITS - correct_set) if task_config.ask_incorrect else correct_set
        target_str = "".join(sorted(target_set))

        user_digits = {c for c in user_answer if c in _ALL_DIGITS}
        is_correct = user_digits == target_set
        user_str = "".join(sorted(user_digits)) or "—"

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        if is_correct:
            header = f"<b>Ответ:</b> {target_str}"
        else:
            header = (
                f"<b>Ваш ответ:</b> {user_str}\n"
                f"<b>Правильный ответ:</b> {target_str}"
            )

        content = Task2324Content.model_validate(exercise.content)

        explanation = header
        if exercise.explanation:
            explanation += (
                f"\n\n<b>Объяснение:</b>\n<blockquote expandable>{exercise.explanation}</blockquote>"
            )
        explanation += (f"\n\n<b>{self._OPTIONS_LABEL}:</b>\n<blockquote expandable>" + "\n".join(
            f"{i + 1}. {opt}" for i, opt in enumerate(content.options)
        ) + "</blockquote>")
        explanation += f"\n\n<b>Текст:</b>\n<blockquote expandable>{content.text}</blockquote>"

        return CheckResult(is_correct=is_correct, explanation=explanation)


class Task23ExamProcessor(_Task2324BaseProcessor):
    """Задание 23 — утверждения о содержании текста."""

    _CORRECT_FORMULATION = (
        "Какие из высказываний соответствуют содержанию текста? Укажите номера ответов."
    )
    _INCORRECT_FORMULATION = (
        "Какие из высказываний <b>не соответствуют</b> содержанию текста? Укажите номера ответов."
    )
    _OPTIONS_LABEL = "Высказывания"


class Task24ExamProcessor(_Task2324BaseProcessor):
    """Задание 24 — утверждения о структуре и языковых особенностях текста."""

    _CORRECT_FORMULATION = (
        "Какие из перечисленных утверждения являются верными? Укажите номера ответов."
    )
    _INCORRECT_FORMULATION = (
        "Какие из перечисленных утверждения являются <b>ошибочными</b>? Укажите номера ответов."
    )
    _OPTIONS_LABEL = "Утверждения"
