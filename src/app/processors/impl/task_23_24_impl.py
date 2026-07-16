import random

from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.formatters import Task2324Formatter
from app.processors.schemas import Task2324Config, Task2324Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

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
    _formatter: Task2324Formatter

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task2324Content.model_validate(exercise.content)
        ask_incorrect = _pick_mode(exercise.answer)

        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.condition(ask_incorrect=ask_incorrect, text=content.text, options=content.options),
                options=None,
            ),
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

        content = Task2324Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.result(
                correct_answer=target_str,
                user_answer=user_str,
                text=content.text,
                options=content.options,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )


class Task23ExamProcessor(_Task2324BaseProcessor):
    """Задание 23 — утверждения о содержании текста."""

    _formatter = Task2324Formatter(23)


class Task24ExamProcessor(_Task2324BaseProcessor):
    """Задание 24 — утверждения о структуре и языковых особенностях текста."""

    _formatter = Task2324Formatter(24)
