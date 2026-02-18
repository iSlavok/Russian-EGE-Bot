import html
from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task6Content, Task6Type
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import check_answer

INSTRUCTIONS = {
    Task6Type.REMOVE: "Отредактируйте предложение: исправьте лексическую ошибку, <b>исключив лишнее слово.</b> "
                      "Выпишите это слово.",
    Task6Type.REPLACE: "Отредактируйте предложение: исправьте лексическую ошибку, "
                       "<b>заменив употреблённое неверно слово.</b> Запишите подобранное слово, соблюдая нормы "
                       "современного русского литературного языка и сохраняя смысл высказывания.",
}


class Task6ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 6.

    Пользователь получает инструкцию и предложение с лексической ошибкой.
    В зависимости от task_type выдается разная инструкция:
    - REMOVE: исправьте лексическую ошибку, исключив лишнее слово
    - REPLACE: исправьте лексическую ошибку, заменив неверно употреблённое слово

    Ответ может быть любым из перечисленных в поле answer (через точку с запятой).

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
            msg = "Current category must have a parent category for Task 6"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)

        exercise = exercises[0]
        content = Task6Content.model_validate(exercise.content)

        instruction = INSTRUCTIONS[content.task_type]

        task_text = f"{instruction}\n\n<i>{content.sentence}</i>"
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

        content = Task6Content.model_validate(exercise.content)

        explanation = (f"{exercise.explanation}\n\n"
                       f"<b>Исходное предложение:</b>\n<i>{content.sentence_with_markup}</i>\n\n"
                       f"<b>Правильное предложение:</b>\n<i>{content.corrected_sentence}</i>")

        if len(correct_answers) == 1 and correct_answers[0].lower() == user_answer.strip().lower():
            explanation = f"<b>Ответ:</b> {correct_answers[0]}\n\n" + explanation
        else:
            if len(correct_answers) == 1:
                explanation = f"<b>Правильный ответ:</b> {correct_answers[0]}\n\n" + explanation
            else:
                explanation = f"<b>Правильные ответы:</b> {' / '.join(correct_answers)}\n\n" + explanation
            explanation = f"<b>Ваш ответ:</b> {html.escape(user_answer, quote=False)}\n" + explanation

        return CheckResult(
            is_correct=is_correct,
            explanation=explanation,
        )
