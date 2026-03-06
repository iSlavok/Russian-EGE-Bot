from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas import TaskN17N20Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

_FORMULATION = (
    "Расставьте все знаки препинания: укажите цифру(-ы), на месте которой(-ых) "
    "в предложении должна(-ы) стоять запятая(-ые)."
)


class _BaseTaskN17N20Processor(BaseTaskProcessor):

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

        content = TaskN17N20Content.model_validate(exercise.content)

        task_text = f"{_FORMULATION}\n\n<i>{content.sentence}</i>"

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=None),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises"
            raise ValueError(msg)
        exercise = user.current_exercises[0]

        user_digits = "".join(sorted(c for c in user_answer if c.isdigit()))
        is_correct = user_digits == exercise.answer

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

        content = TaskN17N20Content.model_validate(exercise.content)

        if is_correct:
            explanation = f"<b>Ответ:</b> {exercise.answer}"
        else:
            explanation = (
                f"<b>Ваш ответ:</b> {user_digits or '—'}\n"
                f"<b>Правильный ответ:</b> {exercise.answer}"
            )

        explanation += (
            f"\n\n<i>{content.correct_sentence}</i>\n\n"
            f"<b>Объяснение:</b>\n<blockquote expandable>{exercise.explanation}</blockquote>"
        )

        return CheckResult(is_correct=is_correct, explanation=explanation)


class Task17ExamProcessor(_BaseTaskN17N20Processor):
    pass


class Task18ExamProcessor(_BaseTaskN17N20Processor):
    pass


class Task19ExamProcessor(_BaseTaskN17N20Processor):
    pass


class Task20ExamProcessor(_BaseTaskN17N20Processor):
    pass
