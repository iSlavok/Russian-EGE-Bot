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
from app.processors.formatters import Task5Formatter
from app.processors.schemas import Task5Content, Task5ExamConfig
from app.schemas import (
    CheckResult,
    ExerciseDTO,
    TaskOption,
    TaskResponse,
    TaskUI,
    UserWithCategoryDTO,
    UserWithExercisesDTO,
)
from app.utils import check_answer

EXAM_SENTENCES_COUNT = 5
EXAM_INITIAL_POOL_SIZE = 50


class Task5DrillProcessor(BaseTaskProcessor):
    """Процессор для тренировочного режима задания 5.

    Пользователь должен выбрать подходящий по смыслу пароним для предложения.
    """

    _formatter = Task5Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        exercise = await self._fetch_exercise(parent_id, user.id)

        content = Task5Content.model_validate(exercise.content)
        options = [
            TaskOption(text=paronym.inflected_form, value=str(i + 1))
            for i, paronym in enumerate(content.paronyms)
        ]

        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.drill_condition(content.sentence), options=options),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        base_result = await self._process_answer_single_exercise(user, user_answer)

        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]
        content = Task5Content.model_validate(exercise.content)

        if not exercise.answer.isdigit():
            raise InvalidExerciseDataError(exercise.id, "answer must be a digit")
        correct_word = content.paronyms[int(exercise.answer) - 1].inflected_form

        return CheckResult(
            is_correct=base_result.is_correct,
            explanation=None,
            result_view=self._formatter.drill_result(
                correct_word=correct_word,
                sentence_template=content.sentence,
                paronym_explanations=[paronym.explanation for paronym in content.paronyms],
                user_answer=user_answer,
                is_correct=base_result.is_correct,
            ),
        )


class Task5ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 5.

    Создает задание из 5 предложений: 4 с правильными словами, 1 с неправильным.
    Пользователь должен ввести правильное слово для предложения с ошибкой.
    """

    _formatter = Task5Formatter()

    @staticmethod
    def _select_exercises_without_word_overlap(
        exercises: Sequence[Exercise],
        limit: int,
    ) -> list[Exercise]:
        """Выбирает упражнения без пересечения слов в поле content['words']."""
        selected: list[Exercise] = []
        used_words: set[str] = set()

        for exercise in exercises:
            content = Task5Content.model_validate(exercise.content)
            words = set(content.words)

            if not words & used_words:
                selected.append(exercise)
                used_words.update(words)

                if len(selected) == limit:
                    break

        return selected

    @staticmethod
    def _shown_pairs(exercises: Sequence[Exercise | ExerciseDTO], wrong_index: int) -> list[tuple[str, str]]:
        """Для каждого предложения — (шаблон, показанное слово): неверное для wrong_index, иначе верное."""
        pairs: list[tuple[str, str]] = []
        for i, exercise in enumerate(exercises):
            content = Task5Content.model_validate(exercise.content)
            if i == wrong_index:
                word = content.paronyms[content.secondary_number - 1].inflected_form
            else:
                if not exercise.answer.isdigit():
                    raise InvalidExerciseDataError(exercise.id, "answer must be a digit")
                word = content.paronyms[int(exercise.answer) - 1].inflected_form
            pairs.append((content.sentence, word))
        return pairs

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        exercises_pool = await self._fetch_exercises(parent_id, user.id, EXAM_INITIAL_POOL_SIZE)

        exercises = self._select_exercises_without_word_overlap(exercises_pool, EXAM_SENTENCES_COUNT)
        if len(exercises) < EXAM_SENTENCES_COUNT:
            raise TaskForUserNotFoundError(user.id)

        wrong_sentence_index = random.randint(0, EXAM_SENTENCES_COUNT - 1)
        shown = self._shown_pairs(exercises, wrong_sentence_index)

        exercise_ids = [ex.id for ex in exercises]
        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.condition(shown), options=None),
            exercise_ids=exercise_ids,
            task_config=Task5ExamConfig(
                exercise_ids=exercise_ids,
                wrong_sentence_index=wrong_sentence_index,
            ),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_SENTENCES_COUNT:
            raise InvalidExerciseCountError(EXAM_SENTENCES_COUNT, len(user.current_exercises or []))

        if user.current_task_config is None:
            raise MissingTaskConfigError

        config = Task5ExamConfig.model_validate(user.current_task_config)
        ordered_exercises = self._get_ordered_exercises(user, config.exercise_ids)

        wrong_exercise = ordered_exercises[config.wrong_sentence_index]
        wrong_content = Task5Content.model_validate(wrong_exercise.content)

        if not wrong_exercise.answer.isdigit():
            raise InvalidExerciseDataError(wrong_exercise.id, "answer must be a digit")
        correct_word = wrong_content.paronyms[int(wrong_exercise.answer) - 1].inflected_form
        wrong_word = wrong_content.paronyms[wrong_content.secondary_number - 1].inflected_form

        is_correct = check_answer(
            user_answer,
            correct_word,
            allow_dash_variations=False,
            allow_space_omission=False,
        )

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, wrong_exercise.id, is_correct, user_answer, solve_time)

        return CheckResult(
            is_correct=is_correct,
            explanation=None,
            result_view=self._formatter.result(
                correct_word=correct_word,
                wrong_word=wrong_word,
                sentence_template=wrong_content.sentence,
                paronym_explanations=[paronym.explanation for paronym in wrong_content.paronyms],
                shown=self._shown_pairs(ordered_exercises, config.wrong_sentence_index),
                user_answer=user_answer,
                is_correct=is_correct,
            ),
        )
