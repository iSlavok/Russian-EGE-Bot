from app.exceptions import NoCurrentExercisesError
from app.processors import BaseTaskProcessor
from app.processors.formatters import Task1Formatter
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

    _formatter = Task1Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task1Content.model_validate(exercise.content)
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

        content = Task1Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            explanation=None,
            result_view=self._formatter.result(content, correct_answers, user_answer, is_correct=is_correct),
        )
