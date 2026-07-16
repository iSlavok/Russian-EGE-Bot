import random
import uuid

from app.exceptions import (
    InvalidExerciseCountError,
    MissingTaskConfigError,
    NoCurrentExercisesError,
    TaskForUserNotFoundError,
)
from app.models import Exercise
from app.processors import BaseTaskProcessor
from app.processors.formatters import Task13Formatter, Task13Sentence
from app.processors.schemas import Task13Content, Task13ExamConfig
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits

EXAM_SENTENCES = 5
CORRECT_COUNT_WEIGHTS = [4, 4, 1]
NI_COUNT_WEIGHTS = [4, 4, 1]

_TOGETHER = "TOGETHER"
_SEPARATE = "SEPARATE"

_MODE_NE = "НЕ"
_MODE_NE_NI = "НЕ/НИ"


class Task13DrillProcessor(BaseTaskProcessor):
    _formatter = Task13Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        exercise = await self._fetch_exercise(parent_id, user.id)

        content = Task13Content.model_validate(exercise.content)
        options = [
            TaskOption(text="Слитно", value=_TOGETHER),
            TaskOption(text="Раздельно", value=_SEPARATE),
        ]

        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.drill_condition(particle=content.particle, sentence=content.sentence),
                options=options,
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

        content = Task13Content.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.drill_result(
                sentence=content.sentence,
                answer=exercise.answer,
                user_answer=user_answer,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )


class Task13ExamProcessor(BaseTaskProcessor):
    _formatter = Task13Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)

        mode = random.choices([_MODE_NE, _MODE_NE_NI], weights=[90, 10])[0]
        answer_type = random.choice([_TOGETHER, _SEPARATE])
        correct_count = random.choices([2, 3, 4], weights=CORRECT_COUNT_WEIGHTS)[0]
        wrong_count = EXAM_SENTENCES - correct_count
        opposite_answer = _SEPARATE if answer_type == _TOGETHER else _TOGETHER

        if mode == _MODE_NE:
            all_exs = await self._fetch_ne_exercises(
                parent_id, user.id, answer_type, opposite_answer, correct_count, wrong_count,
            )
        else:
            all_exs = await self._fetch_ne_ni_exercises(
                parent_id, user.id, answer_type, opposite_answer, correct_count,
            )

        if all_exs is None:
            raise TaskForUserNotFoundError(user.id)

        random.shuffle(all_exs)
        correct_indices = [i for i, ex in enumerate(all_exs) if ex.answer == answer_type]

        sentences = [Task13Content.model_validate(ex.content).sentence for ex in all_exs]
        exercise_ids = [ex.id for ex in all_exs]
        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.condition(mode=mode, answer_type=answer_type, sentences=sentences),
                options=None,
            ),
            exercise_ids=exercise_ids,
            task_config=Task13ExamConfig(
                exercise_ids=exercise_ids,
                correct_indices=correct_indices,
                answer_type=answer_type,
                mode=mode,
            ),
        )

    async def _fetch_ne_exercises(
        self,
        category_id: int,
        user_id: int,
        answer_type: str,
        opposite_answer: str,
        correct_count: int,
        wrong_count: int,
    ) -> list[Exercise] | None:
        correct_exs = list(await self._exercise_selector.select_by_answer_and_content(
            category_id=category_id,
            user_id=user_id,
            answer=answer_type,
            field="particle",
            value="НЕ",
            limit=correct_count,
        ))
        wrong_exs = list(await self._exercise_selector.select_by_answer_and_content(
            category_id=category_id,
            user_id=user_id,
            answer=opposite_answer,
            field="particle",
            value="НЕ",
            limit=wrong_count,
        ))
        if len(correct_exs) < correct_count or len(wrong_exs) < wrong_count:
            return None
        return correct_exs + wrong_exs

    async def _fetch_ne_ni_exercises(
        self,
        category_id: int,
        user_id: int,
        answer_type: str,
        opposite_answer: str,
        correct_count: int,
    ) -> list[Exercise] | None:
        ni_count = random.choices([1, 2, 3], weights=NI_COUNT_WEIGHTS)[0]

        ni_exs = list(await self._exercise_selector.select_by_content_value(
            category_id=category_id,
            user_id=user_id,
            field="particle",
            value="НИ",
            limit=ni_count,
        ))
        if not ni_exs:
            return None
        ni_count = len(ni_exs)

        ni_correct_count = sum(1 for ex in ni_exs if ex.answer == answer_type)

        ne_total = EXAM_SENTENCES - ni_count
        ne_correct_needed = max(1, correct_count - ni_correct_count)
        ne_correct_needed = min(ne_correct_needed, ne_total - 1)
        ne_wrong_needed = ne_total - ne_correct_needed

        ne_correct_exs = list(await self._exercise_selector.select_by_answer_and_content(
            category_id=category_id,
            user_id=user_id,
            answer=answer_type,
            field="particle",
            value="НЕ",
            limit=ne_correct_needed,
        ))
        ne_wrong_exs = list(await self._exercise_selector.select_by_answer_and_content(
            category_id=category_id,
            user_id=user_id,
            answer=opposite_answer,
            field="particle",
            value="НЕ",
            limit=ne_wrong_needed,
        ))

        if len(ne_correct_exs) < ne_correct_needed or len(ne_wrong_exs) < ne_wrong_needed:
            return None

        return ni_exs + ne_correct_exs + ne_wrong_exs

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_SENTENCES:
            raise InvalidExerciseCountError(EXAM_SENTENCES, len(user.current_exercises or []))

        if user.current_task_config is None:
            raise MissingTaskConfigError

        config = Task13ExamConfig.model_validate(user.current_task_config)

        correct_answer = "".join(str(i + 1) for i in sorted(config.correct_indices))
        user_digits = extract_sorted_digits(user_answer)
        is_correct = user_digits == correct_answer

        solve_time = self._compute_solve_time(user)
        ordered_exercises = self._get_ordered_exercises(user, config.exercise_ids)
        group_id = uuid.uuid4()

        sentences: list[Task13Sentence] = []
        for i, ex in enumerate(ordered_exercises):
            is_correct_sentence = i in config.correct_indices
            user_selected = str(i + 1) in user_digits
            sentence_right = user_selected == is_correct_sentence

            content = Task13Content.model_validate(ex.content)
            sentences.append(Task13Sentence(
                sentence=content.sentence,
                answer=ex.answer,
                explanation=ex.explanation or "",
                wrong=not sentence_right,
            ))
            self._record_answer(user, ex.id, sentence_right, user_answer, solve_time, group_id)

        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.result(
                correct_answer=correct_answer,
                user_answer=user_digits,
                sentences=sentences,
                is_correct=is_correct,
            ),
        )
