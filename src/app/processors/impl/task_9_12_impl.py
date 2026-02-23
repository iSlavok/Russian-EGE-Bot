import random
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import Exercise, UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas import TaskN9N12Content, TaskN9N12ExamConfig
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import check_answer

EXAM_ROWS = 5
CORRECT_COUNT_WEIGHTS = [4, 4, 1]
_WORDS_PER_ROW_2 = 2


def _word_display(word: str, letter: str) -> str:
    """Заменяет {letter} на конкретную букву."""
    return word.replace("{letter}", letter)


def _word_gap(word: str) -> str:
    """Заменяет {letter} на .. для показа пропуска."""
    return word.replace("{letter}", "..")


def _word_in_context(word_str: str, context_before: str | None, context_after: str | None) -> str:
    """Составляет строку: контекст_до слово контекст_после."""
    parts = []
    if context_before:
        parts.append(context_before)
    parts.append(word_str)
    if context_after:
        parts.append(context_after)
    return " ".join(parts)


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
    TASK_DESCRIPTION: str = "Выберите правильный вариант ответа, вставив пропущенную букву в слово."

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.parent_id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = TaskN9N12Content.model_validate(exercise.content)

        correct_word = _word_display(content.word, exercise.answer.upper())
        incorrect_word = _word_display(content.word, content.incorrect_letter.upper())

        options = [
            TaskOption(text=correct_word, value=exercise.answer),
            TaskOption(text=incorrect_word, value=content.incorrect_letter),
        ]
        random.shuffle(options)

        word_gap = _word_gap(content.word)
        context_text = _word_in_context(word_gap, content.context_before, content.context_after)
        task_text = f"{self.TASK_DESCRIPTION}\n\n<i>{context_text}</i>"

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=options),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises"
            raise ValueError(msg)
        exercise = user.current_exercises[0]

        is_correct = check_answer(
            user_answer,
            exercise.answer,
            allow_dash_variations=False,
            allow_space_omission=False,
        )

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        self._answer_repository.add(UserAnswer(
            is_correct=is_correct,
            user_response=user_answer,
            solve_time=solve_time,
            user_id=user.id,
            exercise_id=exercise.id,
            category_id=user.current_category_id,
        ))

        content = TaskN9N12Content.model_validate(exercise.content)
        correct_word = _word_display(content.word, exercise.answer.upper())

        if is_correct:
            explanation = f"<b>Ответ:</b> {correct_word}\n\n{exercise.explanation}"
        else:
            incorrect_word = _word_display(content.word, user_answer.upper())
            explanation = (
                f"<b>Ваш ответ:</b> {incorrect_word}\n"
                f"<b>Правильный ответ:</b> {correct_word}\n\n"
                f"{exercise.explanation}"
            )

        return CheckResult(is_correct=is_correct, explanation=explanation)


class _BaseN9N12ExamProcessor(BaseTaskProcessor):
    WORDS_PER_ROW: int

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category"
            raise ValueError(msg)

        category_id = user.current_category.parent_id
        wpr = self.WORDS_PER_ROW

        correct_count = random.choices([2, 3, 4], weights=CORRECT_COUNT_WEIGHTS)[0]
        wrong_count = EXAM_ROWS - correct_count

        correct_exercises = list(
            await self._exercise_repository.get_random_same_answer_groups(
                category_id=category_id,
                group_size=wpr,
                num_groups=correct_count,
            ),
        )

        if len(correct_exercises) < correct_count * wpr:
            raise TaskForUserNotFoundError(user.id)

        rows_by_answer: dict[str, list[Exercise]] = defaultdict(list)
        for ex in correct_exercises:
            rows_by_answer[ex.answer].append(ex)
        correct_rows = list(rows_by_answer.values())

        used_ids = {e.id for e in correct_exercises}

        wrong_pool = list(await self._exercise_repository.get_random(
            category_id=category_id,
            limit=wrong_count * wpr * 3,
        ))
        remaining = [ex for ex in wrong_pool if ex.id not in used_ids]

        wrong_rows = _build_wrong_rows(wrong_count, wpr, remaining)

        if len(wrong_rows) < wrong_count:
            raise TaskForUserNotFoundError(user.id)

        tagged = [(row, True) for row in correct_rows] + [(row, False) for row in wrong_rows]
        random.shuffle(tagged)

        all_rows = [row for row, _ in tagged]
        correct_row_indices = [i for i, (_, is_corr) in enumerate(tagged) if is_corr]

        task_text = (
            "<b>Укажите варианты ответов, в которых во всех словах одного ряда "
            "пропущена одна и та же буква. Запишите номера ответов.</b>\n\n"
        )
        for i, row in enumerate(all_rows, start=1):
            words_display = []
            for ex in row:
                content = TaskN9N12Content.model_validate(ex.content)
                word_str = _word_in_context(
                    _word_gap(content.word),
                    content.context_before,
                    content.context_after,
                )
                words_display.append(word_str)
            task_text += f"{i}) {', '.join(words_display)}\n"

        exercise_ids = [ex.id for row in all_rows for ex in row]
        config = TaskN9N12ExamConfig(
            exercise_ids=exercise_ids,
            correct_row_indices=correct_row_indices,
            words_per_row=wpr,
        )

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=None),
            exercise_ids=exercise_ids,
            task_config=config,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        total_expected = EXAM_ROWS * self.WORDS_PER_ROW
        if not user.current_exercises or len(user.current_exercises) != total_expected:
            msg = f"User must have exactly {total_expected} current exercises for exam"
            raise ValueError(msg)

        if user.current_task_config is None:
            msg = "Task config is required for exam"
            raise ValueError(msg)

        config = TaskN9N12ExamConfig.model_validate(user.current_task_config)
        words_per_row = config.words_per_row

        correct_answer = "".join(str(i + 1) for i in sorted(config.correct_row_indices))
        user_digits = "".join(sorted(c for c in user_answer if c.isdigit()))
        is_correct = user_digits == correct_answer

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        exercises_map = {ex.id: ex for ex in user.current_exercises}
        ordered_exercises = [exercises_map[eid] for eid in config.exercise_ids]

        group_id = uuid.uuid4()

        details = ""
        for row_idx in range(EXAM_ROWS):
            row_exs = ordered_exercises[row_idx * words_per_row:(row_idx + 1) * words_per_row]
            row_num = row_idx + 1
            is_correct_row = row_idx in config.correct_row_indices
            user_selected = str(row_num) in user_digits
            row_right = user_selected == is_correct_row

            details += f"<b>{row_num})</b>\n"

            for ex in row_exs:
                content = TaskN9N12Content.model_validate(ex.content)
                word_str = _word_in_context(
                    _word_display(content.word, f"<b>{ex.answer.upper()}</b>"),
                    content.context_before,
                    content.context_after,
                )
                details += f"{word_str}\n"
                if ex.explanation:
                    details += f"<i>{ex.explanation}</i>\n"
                details += "\n"

            for ex in row_exs:
                self._answer_repository.add(UserAnswer(
                    is_correct=row_right,
                    user_response=user_answer,
                    solve_time=solve_time,
                    group_id=group_id,
                    user_id=user.id,
                    exercise_id=ex.id,
                    category_id=user.current_category_id,
                ))

        if is_correct:
            explanation = f"<b>Ответ: {correct_answer}</b>"
        else:
            explanation = (
                f"Ваш ответ: {user_digits}\n"
                f"<b>Правильный ответ: {correct_answer}</b>"
            )

        explanation += f"\n\n<b>Объяснения:</b>\n<blockquote expandable>{details}</blockquote>"

        return CheckResult(is_correct=is_correct, explanation=explanation)


class Task9DrillProcessor(_BaseN9N12DrillProcessor):
    pass


class Task9ExamProcessor(_BaseN9N12ExamProcessor):
    WORDS_PER_ROW = 3


class Task10DrillProcessor(_BaseN9N12DrillProcessor):
    pass


class Task10ExamProcessor(_BaseN9N12ExamProcessor):
    WORDS_PER_ROW = 3


class Task11DrillProcessor(_BaseN9N12DrillProcessor):
    pass


class Task11ExamProcessor(_BaseN9N12ExamProcessor):
    WORDS_PER_ROW = 2


class Task12DrillProcessor(_BaseN9N12DrillProcessor):
    pass


class Task12ExamProcessor(_BaseN9N12ExamProcessor):
    WORDS_PER_ROW = 2
