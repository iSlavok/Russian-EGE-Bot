import random
import uuid

from app.exceptions import (
    InvalidExerciseCountError,
    MissingTaskConfigError,
    NoCurrentExercisesError,
    TaskForUserNotFoundError,
)
from app.processors import BaseTaskProcessor
from app.processors.formatters import Task14Formatter, Task14Sentence
from app.processors.schemas import Task14DrillContent, Task14ExamConfig, Task14ExamContent
from app.repositories.exercise_filters import answer_eq, answer_ne
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits

EXAM_SENTENCES = 5

TYPE_WEIGHTS = [4, 4, 1]
CORRECT_COUNT_WEIGHTS = [4, 4, 1]

_TOGETHER = "TOGETHER"
_SEPARATE = "SEPARATE"
_HYPHEN = "HYPHEN"

_TASK_TYPES = [_TOGETHER, _SEPARATE, _HYPHEN]


class Task14DrillProcessor(BaseTaskProcessor):
    """Тренировочный режим задания 14.

    Показывает предложение с одним словом в скобках (второе уже раскрыто).
    Три кнопки: слитно / раздельно / через дефис.
    """

    _formatter = Task14Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_exercise(category.id, user.id)

        content = Task14DrillContent.model_validate(exercise.content)
        options = [
            TaskOption(text="Слитно", value=_TOGETHER),
            TaskOption(text="Раздельно", value=_SEPARATE),
            TaskOption(text="Через дефис", value=_HYPHEN),
        ]

        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.drill_condition(content.sentence), options=options),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        is_correct = user_answer == exercise.answer

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task14DrillContent.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            explanation=None,
            result_view=self._formatter.drill_result(
                sentence=content.sentence,
                answer=exercise.answer,
                user_answer=user_answer,
                explanation=exercise.explanation or "",
                is_correct=is_correct,
            ),
        )


class Task14ExamProcessor(BaseTaskProcessor):
    """Экзаменационный режим задания 14.

    Показывает 5 предложений с двумя скобками в каждом.
    Пользователь вводит номера предложений, где оба слова пишутся указанным образом.
    """

    _formatter = Task14Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        category_id = category.id

        answer_type = random.choices(_TASK_TYPES, weights=TYPE_WEIGHTS)[0]
        correct_count = random.choices([2, 3, 4], weights=CORRECT_COUNT_WEIGHTS)[0]
        wrong_count = EXAM_SENTENCES - correct_count

        correct_exs = list(await self._exercise_selector.select_smart_by_group(
            category_id=category_id,
            user_id=user.id,
            limit=correct_count,
            filters=[answer_eq(answer_type)],
        ))
        wrong_exs = list(await self._exercise_selector.select_smart_by_group(
            category_id=category_id,
            user_id=user.id,
            limit=wrong_count,
            filters=[answer_ne(answer_type)],
        ))
        if len(correct_exs) < correct_count or len(wrong_exs) < wrong_count:
            raise TaskForUserNotFoundError(user.id)

        all_exs = correct_exs + wrong_exs
        random.shuffle(all_exs)

        correct_indices = [i for i, ex in enumerate(all_exs) if ex.answer == answer_type]
        sentences = [Task14ExamContent.model_validate(ex.content).sentence for ex in all_exs]

        exercise_ids = [ex.id for ex in all_exs]
        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.condition(answer_type=answer_type, sentences=sentences),
                options=None,
            ),
            exercise_ids=exercise_ids,
            task_config=Task14ExamConfig(
                exercise_ids=exercise_ids,
                correct_indices=correct_indices,
                answer_type=answer_type,
            ),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_SENTENCES:
            raise InvalidExerciseCountError(EXAM_SENTENCES, len(user.current_exercises or []))
        if user.current_task_config is None:
            raise MissingTaskConfigError

        config = Task14ExamConfig.model_validate(user.current_task_config)

        correct_answer = "".join(str(i + 1) for i in sorted(config.correct_indices))
        user_digits = extract_sorted_digits(user_answer)
        is_correct = user_digits == correct_answer

        solve_time = self._compute_solve_time(user)
        ordered_exercises = self._get_ordered_exercises(user, config.exercise_ids)
        group_id = uuid.uuid4()

        sentences: list[Task14Sentence] = []
        for i, ex in enumerate(ordered_exercises):
            is_correct_sentence = i in config.correct_indices
            user_selected = str(i + 1) in user_digits
            sentence_right = user_selected == is_correct_sentence

            content = Task14ExamContent.model_validate(ex.content)
            sentences.append(Task14Sentence(
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
