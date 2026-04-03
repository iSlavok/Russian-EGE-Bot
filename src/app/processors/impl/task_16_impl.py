import random
import uuid

from app.exceptions import (
    InvalidExerciseCountError,
    MissingTaskConfigError,
    NoCurrentExercisesError,
    TaskForUserNotFoundError,
)
from app.processors import BaseTaskProcessor
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

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        exercise = await self._fetch_exercise(parent_id, user.id)

        content = Task16Content.model_validate(exercise.content)

        task_text = (
            "Сколько запятых нужно поставить в предложении?\n\n"
            f"<i>{content.sentence}</i>"
        )

        options = [TaskOption(text=str(i), value=str(i)) for i in range(8)]

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=options, options_per_row=4),
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

        if is_correct:
            explanation = (
                f"<b>Ответ:</b> {exercise.answer}\n\n"
                f"<i>{content.corrected_sentence}</i>\n\n"
                f"{exercise.explanation}"
            )
        else:
            explanation = (
                f"<b>Ваш ответ:</b> {user_answer}\n"
                f"<b>Правильный ответ:</b> {exercise.answer}\n\n"
                f"<i>{content.corrected_sentence}</i>\n\n"
                f"{exercise.explanation}"
            )

        return CheckResult(is_correct=is_correct, explanation=explanation)


class Task16ExamProcessor(BaseTaskProcessor):
    """Экзаменационный режим задания 16.

    Показывает 5 предложений без запятых, из которых 2–4 требуют ровно одной запятой.
    Пользователь вводит номера предложений, в которых нужна ОДНА запятая.
    """

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

        task_text = (
            "Укажите предложения, в которых нужно поставить <b>ОДНУ</b> запятую. "
            "Запишите номера этих предложений.\n\n"
        )
        for i, ex in enumerate(all_exs, start=1):
            content = Task16Content.model_validate(ex.content)
            task_text += f"{i}) {content.sentence}\n"

        exercise_ids = [ex.id for ex in all_exs]
        config = Task16ExamConfig(
            exercise_ids=exercise_ids,
            correct_indices=correct_indices,
        )

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=None),
            exercise_ids=exercise_ids,
            task_config=config,
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
        details = ""

        for i, ex in enumerate(ordered_exercises):
            sentence_num = i + 1
            is_correct_sentence = i in config.correct_indices
            user_selected = str(sentence_num) in user_digits
            sentence_right = user_selected == is_correct_sentence

            content = Task16Content.model_validate(ex.content)
            details += (
                f"<b>{sentence_num})</b> <i>{content.corrected_sentence}</i>\n"
                f"{ex.explanation}\n\n"
            )

            self._record_answer(user, ex.id, sentence_right, user_answer, solve_time, group_id)

        if is_correct:
            explanation = f"<b>Ответ: {correct_answer}</b>"
        else:
            explanation = (
                f"Ваш ответ: {user_digits}\n"
                f"<b>Правильный ответ: {correct_answer}</b>"
            )

        explanation += f"\n\n<b>Объяснения:</b>\n<blockquote expandable>{details}</blockquote>"

        return CheckResult(is_correct=is_correct, explanation=explanation)
