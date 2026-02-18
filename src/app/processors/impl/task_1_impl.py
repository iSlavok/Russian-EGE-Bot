import html
from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task1Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import check_answer


class Task1DrillProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 1.

    Пользователь получает instruction и text, вводит ответ.
    Ответ может быть любым из перечисленных в поле answer (через запятую).

    Правила валидации:
    - Тире в правильном ответе: юзер может пропустить или заменить на пробел
    - Пробел в правильном ответе: юзер может только пропустить (НЕ заменять на тире)
    - Буква ё: юзер может заменить на е
    - Юзер НЕ может добавлять пробелы/тире там, где их нет в правильном ответе
    - Регистр игнорируется
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category for Task 4"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)

        exercise = exercises[0]
        content = Task1Content.model_validate(exercise.content)

        task_text = f"{content.instruction}\n\n<i>{html.escape(content.text, quote=False)}</i>"
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

        correct_answers = [ans.strip() for ans in exercise.answer.split(";")]

        is_correct = any(
            check_answer(user_answer, correct_ans)
            for correct_ans in correct_answers
        )

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

        content = Task1Content.model_validate(exercise.content)
        explanation = f"{content.instruction}\n\n{exercise.explanation}"
        if len(correct_answers) == 1 and correct_answers[0].lower() == user_answer.strip().lower():
            explanation = f"<b>Ответ: {correct_answers[0]}</b>\n\n" + explanation
        else:
            if len(correct_answers) == 1:
                explanation = f"<b>Правильный ответ: {correct_answers[0]}</b>\n\n" + explanation
            else:
                explanation = f"<b>Правильные ответы: {' / '.join(correct_answers)}</b>\n\n" + explanation
            explanation = f"Ваш ответ: {html.escape(user_answer, quote=False)}\n" + explanation

        return CheckResult(
            is_correct=is_correct,
            explanation=explanation,
        )
