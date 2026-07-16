import random

from app.exceptions import MissingTaskConfigError, NoCurrentExercisesError, TaskForUserNotFoundError
from app.processors import BaseTaskProcessor
from app.processors.formatters import Task15Formatter
from app.processors.schemas import Task15DrillContent, Task15ExamConfig, Task15ExamContent
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits

_N = "н"
_NN = "нн"


class Task15DrillProcessor(BaseTaskProcessor):
    """Тренировочный режим задания 15.

    Показывает предложение с пропуском в одном слове.
    Две кнопки с вариантами слова: с Н и с НН — фиксированный порядок.
    """

    _formatter = Task15Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task15DrillContent.model_validate(exercise.content)
        options = [
            TaskOption(text=content.word.format(n=_N.upper()), value=_N),
            TaskOption(text=content.word.format(n=_NN.upper()), value=_NN),
        ]

        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.drill_condition(sentence=content.sentence), options=options),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        is_correct = user_answer == exercise.answer

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task15DrillContent.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.drill_result(
                word=content.word,
                sentence=content.sentence,
                answer=exercise.answer,
                user_answer=user_answer,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )


class Task15ExamProcessor(BaseTaskProcessor):
    """Экзаменационный режим задания 15.

    Показывает предложение с пронумерованными пропусками (1)(2)...
    Тип задания (Н или НН) выбирается рандомно из доступных modes.
    Пользователь вводит номера позиций, где пишется нужный тип.
    """

    _formatter = Task15Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercises = await self._exercise_selector.select_smart_by_group(
            category_id=category.id, user_id=user.id, limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task15ExamContent.model_validate(exercise.content)
        mode = random.choice(content.modes)

        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.condition(mode=mode, sentence=content.sentence),
                options=None,
            ),
            exercise_ids=exercise.id,
            task_config=Task15ExamConfig(mode=mode),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        if user.current_task_config is None:
            raise MissingTaskConfigError

        config = Task15ExamConfig.model_validate(user.current_task_config)
        exercise = user.current_exercises[0]

        mode_answer = config.mode.lower()
        answers = exercise.answer.split(";")
        correct_answer = "".join(str(i + 1) for i, a in enumerate(answers) if a == mode_answer)
        user_digits = extract_sorted_digits(user_answer)
        is_correct = user_digits == correct_answer

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task15ExamContent.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.result(
                correct_answer=correct_answer,
                user_answer=user_digits,
                corrected_sentence=content.corrected_sentence,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )
