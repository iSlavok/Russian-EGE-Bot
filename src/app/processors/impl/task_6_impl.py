from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.formatters import Task6Formatter
from app.processors.schemas import Task6Content
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import check_answer


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

    _formatter = Task6Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task6Content.model_validate(exercise.content)
        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.condition(content), options=None),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        correct_answers = [ans.strip() for ans in exercise.answer.split(";")]
        is_correct = any(check_answer(user_answer, correct_ans) for correct_ans in correct_answers)

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task6Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            explanation=None,
            result_view=self._formatter.result(
                content, correct_answers, user_answer, exercise.explanation or "", is_correct=is_correct,
            ),
        )
