import random
import uuid

from app.exceptions import (
    InvalidExerciseCountError,
    MissingTaskConfigError,
    NoCurrentExercisesError,
    TaskForUserNotFoundError,
)
from app.processors import BaseTaskProcessor
from app.processors.formatters import Task16Formatter, Task16Sentence
from app.processors.schemas import Task16Content, Task16ExamConfig
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits

EXAM_SENTENCES = 5
CORRECT_COUNT_WEIGHTS = [4, 4, 1]

_ANSWER_ONE = "1"


class Task16DrillProcessor(BaseTaskProcessor):
    """Тренировочный режим задания 16.

    Показывает одно предложение без запятых.
    Кнопки 0–7 — количество запятых, которые нужно поставить.
    """

    _formatter = Task16Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        exercise = await self._fetch_exercise(parent_id, user.id)

        content = Task16Content.model_validate(exercise.content)
        options = [TaskOption(text=str(i), value=str(i)) for i in range(8)]

        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.drill_condition(content.sentence),
                options=options,
                options_per_row=4,
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

        content = Task16Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            explanation=None,
            result_view=self._formatter.drill_result(
                answer=exercise.answer,
                user_answer=user_answer,
                corrected_sentence=content.corrected_sentence,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )


class Task16ExamProcessor(BaseTaskProcessor):
    """Экзаменационный режим задания 16.

    Показывает 5 предложений без запятых, из которых 2–4 требуют ровно одной запятой.
    Пользователь вводит номера предложений, в которых нужна ОДНА запятая.
    """

    _formatter = Task16Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)

        correct_count = random.choices([2, 3, 4], weights=CORRECT_COUNT_WEIGHTS)[0]
        wrong_count = EXAM_SENTENCES - correct_count

        correct_exs = list(await self._exercise_selector.select_by_answer(
            category_id=parent_id,
            user_id=user.id,
            answer=_ANSWER_ONE,
            limit=correct_count,
        ))
        wrong_exs = list(await self._exercise_selector.select_excluding_answer(
            category_id=parent_id,
            user_id=user.id,
            exclude=_ANSWER_ONE,
            limit=wrong_count,
        ))
        if len(correct_exs) < correct_count or len(wrong_exs) < wrong_count:
            raise TaskForUserNotFoundError(user.id)

        all_exs = correct_exs + wrong_exs
        random.shuffle(all_exs)

        correct_indices = [i for i, ex in enumerate(all_exs) if ex.answer == _ANSWER_ONE]
        sentences = [Task16Content.model_validate(ex.content).sentence for ex in all_exs]

        exercise_ids = [ex.id for ex in all_exs]
        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.condition(sentences), options=None),
            exercise_ids=exercise_ids,
            task_config=Task16ExamConfig(exercise_ids=exercise_ids, correct_indices=correct_indices),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_SENTENCES:
            raise InvalidExerciseCountError(EXAM_SENTENCES, len(user.current_exercises or []))
        if user.current_task_config is None:
            raise MissingTaskConfigError

        config = Task16ExamConfig.model_validate(user.current_task_config)

        correct_answer = "".join(str(i + 1) for i in sorted(config.correct_indices))
        user_digits = extract_sorted_digits(user_answer)
        is_correct = user_digits == correct_answer

        solve_time = self._compute_solve_time(user)
        ordered_exercises = self._get_ordered_exercises(user, config.exercise_ids)
        group_id = uuid.uuid4()

        sentences: list[Task16Sentence] = []
        for i, ex in enumerate(ordered_exercises):
            is_correct_sentence = i in config.correct_indices
            user_selected = str(i + 1) in user_digits
            sentence_right = user_selected == is_correct_sentence

            content = Task16Content.model_validate(ex.content)
            sentences.append(Task16Sentence(
                corrected_sentence=content.corrected_sentence,
                explanation=ex.explanation or "",
                wrong=not sentence_right,
            ))
            self._record_answer(user, ex.id, sentence_right, user_answer, solve_time, group_id)

        return CheckResult(
            is_correct=is_correct,
            explanation=None,
            result_view=self._formatter.result(
                correct_answer=correct_answer,
                user_answer=user_digits,
                sentences=sentences,
                is_correct=is_correct,
            ),
        )
