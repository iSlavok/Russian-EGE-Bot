from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.schemas import TaskN17N20Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits

_FORMULATION = (
    "Расставьте все знаки препинания: укажите цифру(-ы), на месте которой(-ых) "
    "в предложении должна(-ы) стоять запятая(-ые)."
)


class _BaseTaskN17N20Processor(BaseTaskProcessor):

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = TaskN17N20Content.model_validate(exercise.content)

        task_text = f"{_FORMULATION}\n\n<i>{content.sentence}</i>"

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=None),
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

        if is_correct:
            explanation = f"<b>Ответ:</b> {exercise.answer}"
        else:
            explanation = (
                f"<b>Ваш ответ:</b> {user_digits or '—'}\n"
                f"<b>Правильный ответ:</b> {exercise.answer}"
            )

        explanation += (
            f"\n\n<b>Исходное:</b>\n<i>{content.sentence}</i>"
            f"\n\n<b>С запятыми:</b>\n<i>{content.correct_sentence}</i>"
            f"\n\n<b>Объяснение:</b>\n<blockquote expandable>{exercise.explanation}</blockquote>"
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
