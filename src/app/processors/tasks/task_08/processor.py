import random
import uuid

from app.exceptions import (
    InvalidExerciseCountError,
    MissingTaskConfigError,
    NoCurrentExercisesError,
    TaskForUserNotFoundError,
)
from app.processors import BaseTaskProcessor
from app.repositories.exercise_filters import answer_ne
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_digits

from .formatter import Task8Formatter, Task8Letter
from .schemas import Task8Content, Task8ExamConfig

EXAM_ERROR_COUNT = 5
EXAM_CORRECT_COUNT = 4
EXAM_TOTAL_COUNT = EXAM_ERROR_COUNT + EXAM_CORRECT_COUNT

NO_ERROR_ANSWER = "no_error"


class Task8DrillProcessor(BaseTaskProcessor):
    """Процессор для тренировочного режима задания 8.

    Показывает одно предложение с ошибкой и 10 кнопок с типами ошибок.
    Пользователь должен определить тип грамматической ошибки.
    """

    _formatter = Task8Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)

        exercises = await self._exercise_selector.select_by_content_field(
            category_id=parent_id,
            user_id=user.id,
            field="corrected_sentence",
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task8Content.model_validate(exercise.content)
        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.drill_condition(content.sentence),
                options=self._formatter.drill_options(),
            ),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        is_correct = user_answer == exercise.answer

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task8Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.drill_result(
                correct_type=exercise.answer,
                user_type=user_answer,
                explanation=exercise.explanation or "",
                sentence=content.sentence,
                corrected_sentence=content.corrected_sentence,
                is_correct=is_correct,
            ),
        )


class Task8ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 8.

    Показывает 9 предложений (5 с ошибками + 4 без) и 5 типов ошибок (А-Д).
    Пользователь вводит 5 цифр — номера предложений для каждой буквы.
    """

    _formatter = Task8Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)

        error_exercises = list(await self._exercise_selector.select_smart_distinct_answer(
            category_id=parent_id,
            user_id=user.id,
            limit=EXAM_ERROR_COUNT,
            filters=[answer_ne(NO_ERROR_ANSWER)],
        ))
        if len(error_exercises) < EXAM_ERROR_COUNT:
            raise TaskForUserNotFoundError(user.id)

        correct_exercises = list(await self._exercise_selector.select_by_answer(
            category_id=parent_id,
            user_id=user.id,
            answer=NO_ERROR_ANSWER,
            limit=EXAM_CORRECT_COUNT,
        ))
        if len(correct_exercises) < EXAM_CORRECT_COUNT:
            raise TaskForUserNotFoundError(user.id)

        all_exercises = error_exercises + correct_exercises
        random.shuffle(all_exercises)

        error_type_order = [ex.answer for ex in error_exercises]
        random.shuffle(error_type_order)

        sentences = [Task8Content.model_validate(ex.content).sentence for ex in all_exercises]
        exercise_ids = [ex.id for ex in all_exercises]
        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.condition(error_type_order, sentences), options=None),
            exercise_ids=exercise_ids,
            task_config=Task8ExamConfig(
                exercise_ids=exercise_ids,
                error_type_order=error_type_order,
            ),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_TOTAL_COUNT:
            raise InvalidExerciseCountError(EXAM_TOTAL_COUNT, len(user.current_exercises or []))

        if user.current_task_config is None:
            raise MissingTaskConfigError

        config = Task8ExamConfig.model_validate(user.current_task_config)
        ordered_exercises = self._get_ordered_exercises(user, config.exercise_ids)

        exercise_by_type = {
            ex.answer: (i, ex)
            for i, ex in enumerate(ordered_exercises, start=1)
            if ex.answer != NO_ERROR_ANSWER
        }
        correct_answer = "".join(str(exercise_by_type[error_type][0]) for error_type in config.error_type_order)

        user_digits = extract_digits(user_answer)
        is_correct = user_digits == correct_answer

        solve_time = self._compute_solve_time(user)
        group_id = uuid.uuid4()
        user_selected = {int(c) for c in user_digits if 1 <= int(c) <= EXAM_TOTAL_COUNT}

        for i, exercise in enumerate(ordered_exercises, start=1):
            if exercise.answer != NO_ERROR_ANSWER:
                error_idx = config.error_type_order.index(exercise.answer)
                word_correct = len(user_digits) > error_idx and user_digits[error_idx] == str(i)
            else:
                word_correct = i not in user_selected
            self._record_answer(user, exercise.id, word_correct, user_answer, solve_time, group_id)

        letters = []
        for error_idx, error_type in enumerate(config.error_type_order):
            position, exercise = exercise_by_type[error_type]
            content = Task8Content.model_validate(exercise.content)
            wrong = error_idx >= len(user_digits) or user_digits[error_idx] != correct_answer[error_idx]
            letters.append(Task8Letter(
                error_type=error_type,
                position=position,
                explanation=exercise.explanation or "",
                sentence=content.sentence,
                corrected_sentence=content.corrected_sentence,
                wrong=wrong,
            ))

        sentences = [Task8Content.model_validate(ex.content).sentence for ex in ordered_exercises]
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.result(
                correct_answer=correct_answer,
                user_answer=user_digits,
                letters=letters,
                sentences=sentences,
                is_correct=is_correct,
            ),
        )
