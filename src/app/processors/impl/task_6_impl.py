import html

from app.exceptions import NoCurrentExercisesError
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
        parent_id = self._require_parent_category_id(user)
        exercise = await self._fetch_random_exercise(parent_id, user.id)

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
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        correct_answers = [ans.strip() for ans in exercise.answer.split(";")]

        is_correct = any(
            check_answer(user_answer, correct_ans)
            for correct_ans in correct_answers
        )

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

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
