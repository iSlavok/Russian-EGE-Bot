import random
from collections.abc import Sequence

from app.exceptions import (
    InvalidExerciseCountError,
    InvalidExerciseDataError,
    MissingTaskConfigError,
    NoCurrentExercisesError,
    TaskForUserNotFoundError,
)
from app.models import Exercise
from app.processors import BaseTaskProcessor
from app.schemas import (
    CheckResult,
    ExerciseDTO,
    TaskOption,
    TaskResponse,
    TaskUI,
    UserWithExercisesDTO,
)
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import check_answer

from .formatter import Task7Formatter
from .schemas import Task7Content, Task7ExamConfig

EXAM_PHRASES_COUNT = 5


class Task7DrillProcessor(BaseTaskProcessor):
    """Процессор для тренировочного режима задания 7.

    Показывает одну фразу с двумя вариантами ответа в кнопках.
    Используются только упражнения, где incorrect_answer не null.
    """

    _formatter = Task7Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)

        exercises = await self._exercise_selector.select_by_content_field(
            category_id=parent_id,
            user_id=user.id,
            field="incorrect_answer",
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task7Content.model_validate(exercise.content)
        if content.incorrect_answer is None:
            raise InvalidExerciseDataError(exercise.id, "no incorrect_answer in content")

        correct_phrase = content.phrase.format(word=exercise.answer.upper())
        incorrect_phrase = content.phrase.format(word=content.incorrect_answer.upper())
        options = [
            TaskOption(text=correct_phrase, value=exercise.answer),
            TaskOption(text=incorrect_phrase, value=content.incorrect_answer),
        ]
        random.shuffle(options)

        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.drill_condition(), options=options),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        is_correct = check_answer(
            user_answer,
            exercise.answer,
            allow_dash_variations=False,
            allow_space_omission=False,
        )

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task7Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.drill_result(
                correct_word=exercise.answer,
                phrase_template=content.phrase,
                explanation=exercise.explanation or "",
                user_answer=user_answer,
                is_correct=is_correct,
            ),
        )


class Task7ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 7.

    Показывает 5 фраз, в одной из которых допущена грамматическая ошибка.
    Пользователь должен найти ошибку и ввести правильный ответ.
    Фильтрация (distinct group_id, наличие incorrect_answer) — на уровне БД.
    Записывает UserAnswer только для фразы с ошибкой.
    """

    _formatter = Task7Formatter()

    @staticmethod
    def _shown_pairs(exercises: Sequence[Exercise | ExerciseDTO], wrong_index: int) -> list[tuple[str, str]]:
        """Для каждого словосочетания — (шаблон, показанное слово): неверное для wrong_index, иначе верное."""
        pairs: list[tuple[str, str]] = []
        for i, exercise in enumerate(exercises):
            content = Task7Content.model_validate(exercise.content)
            word = (content.incorrect_answer or exercise.answer) if i == wrong_index else exercise.answer
            pairs.append((content.phrase, word))
        return pairs

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)

        wrong_exercises = await self._exercise_selector.select_by_content_field(
            category_id=parent_id,
            user_id=user.id,
            field="incorrect_answer",
            limit=1,
        )
        if not wrong_exercises:
            raise TaskForUserNotFoundError(user.id)
        wrong_exercise = wrong_exercises[0]

        filler = await self._exercise_repository.get_random_distinct_group_filler(
            category_id=parent_id,
            limit=EXAM_PHRASES_COUNT - 1,
            exclude_ids=[wrong_exercise.id],
            exclude_group_ids=[wrong_exercise.group_id] if wrong_exercise.group_id else None,
        )
        if len(filler) < EXAM_PHRASES_COUNT - 1:
            raise TaskForUserNotFoundError(user.id)

        exercises = list(filler)
        wrong_phrase_index = random.randint(0, EXAM_PHRASES_COUNT - 1)
        exercises.insert(wrong_phrase_index, wrong_exercise)

        shown = self._shown_pairs(exercises, wrong_phrase_index)
        exercise_ids = [ex.id for ex in exercises]
        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.condition(shown), options=None),
            exercise_ids=exercise_ids,
            task_config=Task7ExamConfig(
                exercise_ids=exercise_ids,
                wrong_phrase_index=wrong_phrase_index,
            ),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_PHRASES_COUNT:
            raise InvalidExerciseCountError(EXAM_PHRASES_COUNT, len(user.current_exercises or []))

        if user.current_task_config is None:
            raise MissingTaskConfigError

        config = Task7ExamConfig.model_validate(user.current_task_config)
        ordered_exercises = self._get_ordered_exercises(user, config.exercise_ids)

        wrong_exercise = ordered_exercises[config.wrong_phrase_index]

        is_correct = check_answer(
            user_answer,
            wrong_exercise.answer,
            allow_dash_variations=False,
            allow_space_omission=False,
            allow_yo_normalization=True,
        )

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, wrong_exercise.id, is_correct, user_answer, solve_time)

        wrong_content = Task7Content.model_validate(wrong_exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.result(
                correct_word=wrong_exercise.answer,
                phrase_template=wrong_content.phrase,
                explanation=wrong_exercise.explanation or "",
                shown=self._shown_pairs(ordered_exercises, config.wrong_phrase_index),
                user_answer=user_answer,
                is_correct=is_correct,
            ),
        )
