from app.exceptions import NoCurrentExercisesError, TaskForUserNotFoundError
from app.processors import BaseTaskProcessor
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits

from .formatter import Task21Formatter
from .schemas import Task21DrillContent, Task21ExamContent


class Task21DrillProcessor(BaseTaskProcessor):
    """Тренировочный режим задания 21.

    Показывает одно предложение. Кнопки — правила постановки знака.
    Ответ — одно правило (например, SUBJ_PRED).
    """

    _formatter = Task21Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task21DrillContent.model_validate(exercise.content)
        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.drill_condition(task_type=content.task_type, text=content.text),
                options=self._formatter.drill_options(content.task_type),
                options_per_row=self._formatter.drill_options_per_row(content.task_type),
            ),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        is_correct = user_answer == exercise.answer

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task21DrillContent.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.drill_result(
                task_type=content.task_type,
                answer=exercise.answer,
                user_answer=user_answer,
                text=content.text,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )


class Task21ExamProcessor(BaseTaskProcessor):
    """Экзаменационный режим задания 21.

    Показывает текст из нескольких пронумерованных предложений.
    Пользователь вводит номера предложений, где знак стоит по одному правилу.
    """

    _formatter = Task21Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercises = await self._exercise_selector.select_smart_by_group(
            category_id=category.id, user_id=user.id, limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task21ExamContent.model_validate(exercise.content)
        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.condition(task_type=content.task_type, full_text=content.full_text),
                options=None,
            ),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        user_digits = extract_sorted_digits(user_answer)
        is_correct = user_digits == exercise.answer

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task21ExamContent.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.result(
                task_type=content.task_type,
                answer=exercise.answer,
                answer_rule=content.answer_rule,
                user_answer=user_digits,
                full_text=content.full_text,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )
