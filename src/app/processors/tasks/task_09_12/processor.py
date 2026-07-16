import random
import uuid
from collections import defaultdict

from app.exceptions import (
    InvalidExerciseCountError,
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
    UserWithCategoryDTO,
    UserWithExercisesDTO,
)
from app.utils import check_answer, extract_sorted_digits

from .formatter import N9N12Row, N9N12Word, TaskN9N12Formatter
from .schemas import TaskN9N12Content, TaskN9N12ExamConfig

EXAM_ROWS = 5
CORRECT_COUNT_WEIGHTS = [4, 4, 1]
_WORDS_PER_ROW_2 = 2


def _word_display(word: str, letter: str) -> str:
    """Заменяет {letter} на конкретную букву (для текста кнопок)."""
    return word.replace("{letter}", letter)


def _word_of(exercise: Exercise | ExerciseDTO) -> N9N12Word:
    content = TaskN9N12Content.model_validate(exercise.content)
    return N9N12Word(
        template=content.word,
        answer_letter=exercise.answer,
        context_before=content.context_before,
        context_after=content.context_after,
        explanation=exercise.explanation or "",
    )


def _get_incorrect_letter(ex: Exercise) -> str:
    """Извлекает incorrect_letter из content упражнения."""
    content = TaskN9N12Content.model_validate(ex.content)
    return content.incorrect_letter


def _build_confusing_row_2(
    by_answer: dict[str, list[Exercise]],
    by_incorrect: dict[str, list[Exercise]],
    used_ids: set[int],
) -> list[Exercise] | None:
    """2-word wrong row: word1.answer=A, word2.incorrect_letter=A (answer≠A)."""
    letters = list(by_answer.keys())
    random.shuffle(letters)

    for letter in letters:
        cands_correct = [e for e in by_answer[letter] if e.id not in used_ids]
        cands_confuse = [e for e in by_incorrect[letter]
                         if e.id not in used_ids and e.answer != letter]
        if cands_correct and cands_confuse:
            row = [cands_correct[0], cands_confuse[0]]
            random.shuffle(row)
            return row

    all_remaining = [e for exs in by_answer.values() for e in exs if e.id not in used_ids]
    random.shuffle(all_remaining)
    for i, ex1 in enumerate(all_remaining):
        for ex2 in all_remaining[i + 1:]:
            if ex1.answer != ex2.answer:
                row = [ex1, ex2]
                random.shuffle(row)
                return row
    return None


def _build_confusing_row_3(
    by_answer: dict[str, list[Exercise]],
    by_incorrect: dict[str, list[Exercise]],
    used_ids: set[int],
) -> list[Exercise] | None:
    """3-word wrong row: путающие комбинации вокруг одной буквы."""
    letters = list(by_incorrect.keys())
    random.shuffle(letters)

    for letter in letters:
        cands_correct = [e for e in by_answer.get(letter, []) if e.id not in used_ids]
        cands_confuse = [e for e in by_incorrect[letter]
                         if e.id not in used_ids and e.answer != letter]

        strategies = [(2, 1), (1, 2), (0, 3)]
        random.shuffle(strategies)

        for n_c, n_i in strategies:
            if len(cands_correct) >= n_c and len(cands_confuse) >= n_i:
                row = cands_correct[:n_c] + cands_confuse[:n_i]
                if len({e.answer for e in row}) > 1:
                    random.shuffle(row)
                    return row

    all_remaining = [e for exs in by_answer.values() for e in exs if e.id not in used_ids]
    random.shuffle(all_remaining)
    for i in range(len(all_remaining) - 2):
        triple = all_remaining[i:i + 3]
        if len({e.answer for e in triple}) > 1:
            random.shuffle(triple)
            return triple
    return None


def _build_wrong_rows(
    wrong_count: int,
    words_per_row: int,
    remaining: list[Exercise],
) -> list[list[Exercise]]:
    """Строит неправильные ряды для экзамена из оставшихся упражнений."""
    by_answer: dict[str, list[Exercise]] = defaultdict(list)
    by_incorrect: dict[str, list[Exercise]] = defaultdict(list)

    for ex in remaining:
        by_answer[ex.answer].append(ex)
        by_incorrect[_get_incorrect_letter(ex)].append(ex)

    rows: list[list[Exercise]] = []
    used_ids: set[int] = set()

    builder = _build_confusing_row_2 if words_per_row == _WORDS_PER_ROW_2 else _build_confusing_row_3

    for _ in range(wrong_count):
        row = builder(by_answer, by_incorrect, used_ids)
        if row is None:
            break
        rows.append(row)
        used_ids.update(e.id for e in row)

    return rows


class _BaseN9N12DrillProcessor(BaseTaskProcessor):
    _formatter: TaskN9N12Formatter

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        exercise = await self._fetch_exercise(parent_id, user.id)

        content = TaskN9N12Content.model_validate(exercise.content)
        options = [
            TaskOption(text=_word_display(content.word, exercise.answer.upper()), value=exercise.answer),
            TaskOption(text=_word_display(content.word, content.incorrect_letter.upper()),
                       value=content.incorrect_letter),
        ]
        random.shuffle(options)

        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.drill_condition(_word_of(exercise)), options=options),
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

        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.drill_result(
                word=_word_of(exercise), user_letter=user_answer, is_correct=is_correct,
            ),
        )


class _BaseN9N12ExamProcessor(BaseTaskProcessor):
    WORDS_PER_ROW: int
    _formatter: TaskN9N12Formatter

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        wpr = self.WORDS_PER_ROW

        correct_count = random.choices([2, 3, 4], weights=CORRECT_COUNT_WEIGHTS)[0]
        wrong_count = EXAM_ROWS - correct_count

        correct_rows = await self._exercise_selector.select_smart_same_answer_groups(
            category_id=parent_id,
            user_id=user.id,
            group_size=wpr,
            num_groups=correct_count,
        )
        if len(correct_rows) < correct_count:
            raise TaskForUserNotFoundError(user.id)

        used_ids = {e.id for row in correct_rows for e in row}
        wrong_pool = list(await self._fetch_exercises(parent_id, user.id, wrong_count * wpr * 5))
        remaining = [ex for ex in wrong_pool if ex.id not in used_ids]

        wrong_rows = _build_wrong_rows(wrong_count, wpr, remaining)
        if len(wrong_rows) < wrong_count:
            raise TaskForUserNotFoundError(user.id)

        tagged = [(row, True) for row in correct_rows] + [(row, False) for row in wrong_rows]
        random.shuffle(tagged)

        all_rows = [row for row, _ in tagged]
        correct_row_indices = [i for i, (_, is_corr) in enumerate(tagged) if is_corr]

        rows = [N9N12Row(words=[_word_of(ex) for ex in row]) for row in all_rows]
        exercise_ids = [ex.id for row in all_rows for ex in row]
        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.condition(rows), options=None),
            exercise_ids=exercise_ids,
            task_config=TaskN9N12ExamConfig(
                exercise_ids=exercise_ids,
                correct_row_indices=correct_row_indices,
                words_per_row=wpr,
            ),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        total_expected = EXAM_ROWS * self.WORDS_PER_ROW
        if not user.current_exercises or len(user.current_exercises) != total_expected:
            raise InvalidExerciseCountError(total_expected, len(user.current_exercises or []))

        if user.current_task_config is None:
            raise MissingTaskConfigError

        config = TaskN9N12ExamConfig.model_validate(user.current_task_config)
        wpr = config.words_per_row

        correct_answer = "".join(str(i + 1) for i in sorted(config.correct_row_indices))
        user_digits = extract_sorted_digits(user_answer)
        is_correct = user_digits == correct_answer

        solve_time = self._compute_solve_time(user)
        ordered_exercises = self._get_ordered_exercises(user, config.exercise_ids)
        group_id = uuid.uuid4()

        rows: list[N9N12Row] = []
        for row_idx in range(EXAM_ROWS):
            row_exs = ordered_exercises[row_idx * wpr:(row_idx + 1) * wpr]
            is_answer_row = row_idx in config.correct_row_indices
            user_selected = str(row_idx + 1) in user_digits
            row_right = user_selected == is_answer_row

            rows.append(N9N12Row(words=[_word_of(ex) for ex in row_exs], wrong=not row_right))
            for ex in row_exs:
                self._record_answer(user, ex.id, row_right, user_answer, solve_time, group_id)

        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.result(
                correct_answer=correct_answer, user_answer=user_digits, rows=rows, is_correct=is_correct,
            ),
        )


class Task9DrillProcessor(_BaseN9N12DrillProcessor):
    _formatter = TaskN9N12Formatter(9)


class Task9ExamProcessor(_BaseN9N12ExamProcessor):
    WORDS_PER_ROW = 3
    _formatter = TaskN9N12Formatter(9)


class Task10DrillProcessor(_BaseN9N12DrillProcessor):
    _formatter = TaskN9N12Formatter(10)


class Task10ExamProcessor(_BaseN9N12ExamProcessor):
    WORDS_PER_ROW = 3
    _formatter = TaskN9N12Formatter(10)


class Task11DrillProcessor(_BaseN9N12DrillProcessor):
    _formatter = TaskN9N12Formatter(11)


class Task11ExamProcessor(_BaseN9N12ExamProcessor):
    WORDS_PER_ROW = 2
    _formatter = TaskN9N12Formatter(11)


class Task12DrillProcessor(_BaseN9N12DrillProcessor):
    _formatter = TaskN9N12Formatter(12)


class Task12ExamProcessor(_BaseN9N12ExamProcessor):
    WORDS_PER_ROW = 2
    _formatter = TaskN9N12Formatter(12)
