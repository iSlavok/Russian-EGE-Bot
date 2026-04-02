import html
import random

from app.exceptions import (
    InvalidExerciseCountError,
    InvalidExerciseDataError,
    MissingTaskConfigError,
    NoCurrentExercisesError,
    TaskForUserNotFoundError,
)
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task7Content, Task7ExamConfig
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import check_answer

EXAM_PHRASES_COUNT = 5


class Task7DrillProcessor(BaseTaskProcessor):
    """Процессор для тренировочного режима задания 7.

    Показывает одну фразу с двумя вариантами ответа в кнопках.
    Используются только упражнения, где incorrect_answer не null.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)

        exercises = await self._exercise_repository.get_random_with_content_filter(
            category_id=parent_id,
            content_field="incorrect_answer",
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

        task_text = "Выберите словосочетание, в котором нет грамматической ошибки."

        return TaskResponse(
            task_ui=TaskUI(
                text=task_text,
                options=options,
            ),
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
        correct_phrase = content.phrase.format(word=f"{exercise.answer.upper()}")

        if is_correct:
            explanation = f"<b>Ответ:</b> {correct_phrase}\n\n{exercise.explanation}"
        else:
            user_answer_phrase = content.phrase.format(word=f"{user_answer.upper()}")
            explanation = (f"<b>Ваш ответ:</b> {user_answer_phrase}\n"
                           f"<b>Правильный ответ:</b> {correct_phrase}\n\n"
                           f"{exercise.explanation}")

        return CheckResult(
            is_correct=is_correct,
            explanation=explanation,
        )


class Task7ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 7.

    Показывает 5 фраз, в одной из которых допущена грамматическая ошибка.
    Пользователь должен найти ошибку и ввести правильный ответ.
    Фильтрация (distinct group_id, наличие incorrect_answer) — на уровне БД.
    Записывает UserAnswer только для фразы с ошибкой.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)

        exercises = await self._exercise_repository.get_random_distinct_group(
            category_id=parent_id,
            limit=EXAM_PHRASES_COUNT,
            require_one_with_content_field="incorrect_answer",
        )

        if len(exercises) < EXAM_PHRASES_COUNT:
            raise TaskForUserNotFoundError(user.id)

        exercises = list(exercises)

        wrong_phrase_index = random.randint(0, EXAM_PHRASES_COUNT - 1)
        if wrong_phrase_index != 0:
            exercises[0], exercises[wrong_phrase_index] = exercises[wrong_phrase_index], exercises[0]

        phrases = []
        for i, exercise in enumerate(exercises):
            content = Task7Content.model_validate(exercise.content)

            if i == wrong_phrase_index:
                word = content.incorrect_answer or exercise.answer
                phrase = content.phrase.format(word=f"<b>{word.upper()}</b>")
            else:
                phrase = content.phrase.format(word=f"<b>{exercise.answer.upper()}</b>")

            phrases.append(phrase)

        task_text = (
            "В одном из выделенных ниже слов допущена грамматическая ошибка. "
            "Исправьте ошибку и запишите слово правильно.\n\n"
        )
        for i, phrase in enumerate(phrases, start=1):
            task_text += f"{i}) {phrase}\n"

        exercise_ids = [ex.id for ex in exercises]
        return TaskResponse(
            task_ui=TaskUI(
                text=task_text,
                options=None,
            ),
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
        correct_phrase = wrong_content.phrase.format(word=f"{wrong_exercise.answer.upper()}")

        explanation = f"{correct_phrase}\n\n{wrong_exercise.explanation}"

        if not is_correct:
            explanation = (
                f"<b>Ваш ответ:</b> {html.escape(user_answer, quote=False)}\n"
                f"<b>Правильный ответ:</b> {wrong_exercise.answer}\n\n"
                + explanation
            )
        else:
            explanation = f"<b>Ответ:</b> {wrong_exercise.answer}\n\n" + explanation

        return CheckResult(
            is_correct=is_correct,
            explanation=explanation,
        )
