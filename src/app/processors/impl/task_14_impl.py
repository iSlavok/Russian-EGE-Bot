import random
import uuid

from app.exceptions import (
    InvalidExerciseCountError,
    MissingTaskConfigError,
    NoCurrentExercisesError,
    TaskForUserNotFoundError,
)
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task14DrillContent, Task14ExamConfig, Task14ExamContent
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits

EXAM_SENTENCES = 5

TYPE_WEIGHTS = [4, 4, 1]

CORRECT_COUNT_WEIGHTS = [4, 4, 1]

_TOGETHER = "TOGETHER"
_SEPARATE = "SEPARATE"
_HYPHEN = "HYPHEN"
_MIXED = "MIXED"

_TASK_TYPES = [_TOGETHER, _SEPARATE, _HYPHEN]

_ANSWER_DISPLAY = {
    _TOGETHER: "слитно",
    _SEPARATE: "раздельно",
    _HYPHEN: "через дефис",
}


class Task14DrillProcessor(BaseTaskProcessor):
    """Тренировочный режим задания 14.

    Показывает предложение с одним словом в скобках (второе уже раскрыто).
    Три кнопки: слитно / раздельно / через дефис.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_random_exercise(category.id, user.id)

        content = Task14DrillContent.model_validate(exercise.content)

        task_text = (
            "Определите написание слова в скобках.\n\n"
            f"<i>{content.sentence}</i>"
        )

        options = [
            TaskOption(text="Слитно", value=_TOGETHER),
            TaskOption(text="Раздельно", value=_SEPARATE),
            TaskOption(text="Через дефис", value=_HYPHEN),
        ]

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=options),
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
        correct_display = _ANSWER_DISPLAY[exercise.answer]

        if is_correct:
            explanation = (
                f"<b>Ответ:</b> {correct_display}\n\n"
                f"<i>{content.sentence}</i>\n\n"
                f"{exercise.explanation}"
            )
        else:
            user_display = _ANSWER_DISPLAY.get(user_answer, user_answer)
            explanation = (
                f"<b>Ваш ответ:</b> {user_display}\n"
                f"<b>Правильный ответ:</b> {correct_display}\n\n"
                f"<i>{content.sentence}</i>\n\n"
                f"{exercise.explanation}"
            )

        return CheckResult(is_correct=is_correct, explanation=explanation)


class Task14ExamProcessor(BaseTaskProcessor):
    """Экзаменационный режим задания 14.

    Показывает 5 предложений с двумя скобками в каждом.
    Пользователь вводит номера предложений, где оба слова пишутся указанным образом.

    Логика подбора:
      1. Выбирается целевой тип (TOGETHER/SEPARATE/HYPHEN) с весами 4:4:1.
      2. Выбирается количество правильных предложений (2/3/4) с весами 4:4:1.
      3. «Правильные» — упражнения с answer == target_type.
      4. «Неправильные» — упражнения с answer != target_type (MIXED или другой тип),
         по одному от каждого доступного неправильного типа, затем случайный выбор нужного кол-ва.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        category_id = category.id

        answer_type = random.choices(_TASK_TYPES, weights=TYPE_WEIGHTS)[0]
        correct_count = random.choices([2, 3, 4], weights=CORRECT_COUNT_WEIGHTS)[0]
        wrong_count = EXAM_SENTENCES - correct_count

        correct_exs = list(await self._exercise_repository.get_random_by_answer(
            category_id=category_id,
            answer=answer_type,
            limit=correct_count,
        ))

        wrong_exs = list(await self._exercise_repository.get_random_excluding_answer(
            category_id=category_id,
            exclude_answer=answer_type,
            limit=wrong_count,
        ))

        if len(correct_exs) < correct_count or len(wrong_exs) < wrong_count:
            raise TaskForUserNotFoundError(user.id)

        all_exs = correct_exs + wrong_exs
        random.shuffle(all_exs)

        correct_indices = [i for i, ex in enumerate(all_exs) if ex.answer == answer_type]
        answer_display = _ANSWER_DISPLAY[answer_type]

        task_text = (
            f"Укажите варианты ответов, в которых оба выделенных слова пишутся "
            f"<b>{answer_display.upper()}</b>. Запишите номера ответов.\n\n"
        )
        for i, ex in enumerate(all_exs, start=1):
            content = Task14ExamContent.model_validate(ex.content)
            task_text += f"{i}) {content.sentence}\n"

        exercise_ids = [ex.id for ex in all_exs]
        config = Task14ExamConfig(
            exercise_ids=exercise_ids,
            correct_indices=correct_indices,
            answer_type=answer_type,
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

        config = Task14ExamConfig.model_validate(user.current_task_config)

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

            content = Task14ExamContent.model_validate(ex.content)

            details += f"<b>{sentence_num})</b> <i>{content.sentence}</i>\n"
            details += f"{ex.explanation}\n\n"

            self._record_answer(user, ex.id, sentence_right, user_answer, solve_time, group_id)

        if is_correct:
            explanation = f"<b>Ответ: {correct_answer}</b>"
        else:
            explanation = (
                f"Ваш ответ: {user_digits}\n"
                f"<b>Правильный ответ: {correct_answer}</b>"
            )

        explanation += f"\n\n<b>Объяснение:</b>\n<blockquote expandable>{details}</blockquote>"

        return CheckResult(is_correct=is_correct, explanation=explanation)
