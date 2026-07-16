from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.formatters import TaskN17N20Formatter
from app.processors.schemas import TaskN17N20Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits


class _BaseTaskN17N20Processor(BaseTaskProcessor):
    _formatter: TaskN17N20Formatter

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = TaskN17N20Content.model_validate(exercise.content)
        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.condition(content.sentence), options=None),
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

        content = TaskN17N20Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            explanation=None,
            result_view=self._formatter.result(
                correct_answer=exercise.answer,
                user_answer=user_digits,
                correct_sentence=content.correct_sentence,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )


class Task17ExamProcessor(_BaseTaskN17N20Processor):
    _formatter = TaskN17N20Formatter(17)


class Task18ExamProcessor(_BaseTaskN17N20Processor):
    _formatter = TaskN17N20Formatter(18)


class Task19ExamProcessor(_BaseTaskN17N20Processor):
    _formatter = TaskN17N20Formatter(19)


class Task20ExamProcessor(_BaseTaskN17N20Processor):
    _formatter = TaskN17N20Formatter(20)
