import html
import random
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import Exercise, UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task5Content, Task5ExamConfig
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import check_answer

EXAM_SENTENCES_COUNT = 5
EXAM_INITIAL_POOL_SIZE = 50


class Task5DrillProcessor(BaseTaskProcessor):
    """Процессор для тренировочного режима задания 5.

    Пользователь должен выбрать подходящий по смыслу пароним для предложения.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category for Task 5"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.parent_id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task5Content.model_validate(exercise.content)

        word_placeholder = html.escape("< . . . >", quote=False)
        sentence = content.sentence.format(word=word_placeholder)

        options = [
            TaskOption(text=paronym.inflected_form, value=str(i + 1))
            for i, paronym in enumerate(content.paronyms)
        ]

        task_text = (
            "В предложении пропущено слово. Выберите из предложенных паронимов подходящее по смыслу.\n\n"
            f"{sentence}"
        )

        return TaskResponse(
            task_ui=TaskUI(
                text=task_text,
                options=options,
            ),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        base_result = await self._process_answer_single_exercise(user, user_answer)

        if user.current_exercises:
            exercise = user.current_exercises[0]
            content = Task5Content.model_validate(exercise.content)

            if not exercise.answer.isdigit():
                msg = f"Exercise answer must be a digit (exercise {exercise.id})"
                raise ValueError(msg)
            correct_answer_index = int(exercise.answer) - 1
            correct_word = content.paronyms[correct_answer_index].inflected_form

            word_text = correct_word.lower()
            if content.sentence.lstrip().startswith("{word}"):
                word_text = word_text.capitalize()
            sentence_with_correct_word = content.sentence.format(
                word=f"<u>{word_text}</u>",
            )

            paronym_explanations = "\n\n".join(
                paronym.explanation for paronym in content.paronyms
            )

            explanation = f"{sentence_with_correct_word}\n\n\n{paronym_explanations}"

            return CheckResult(
                is_correct=base_result.is_correct,
                explanation=explanation,
            )

        return base_result


class Task5ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 5.

    Создает задание из 5 предложений: 4 с правильными словами, 1 с неправильным.
    Пользователь должен ввести правильное слово для предложения с ошибкой.
    """
    @staticmethod
    def _select_exercises_without_word_overlap(
        exercises: Sequence[Exercise],
        limit: int,
    ) -> list[Exercise]:
        """Выбирает упражнения без пересечения слов в поле content['words'].

        Args:
            exercises: список упражнений для фильтрации
            limit: необходимое количество упражнений

        Returns:
            Список упражнений без пересечения слов
        """
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

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category for Task 5"
            raise ValueError(msg)

        exercises_pool = await self._exercise_repository.get_random(
            category_id=user.current_category.parent_id,
            limit=EXAM_INITIAL_POOL_SIZE,
        )

        exercises = self._select_exercises_without_word_overlap(exercises_pool, EXAM_SENTENCES_COUNT)

        if len(exercises) < EXAM_SENTENCES_COUNT:
            raise TaskForUserNotFoundError(user.id)

        wrong_sentence_index = random.randint(0, EXAM_SENTENCES_COUNT - 1)

        sentences = []
        for i, exercise in enumerate(exercises):
            content = Task5Content.model_validate(exercise.content)

            if i == wrong_sentence_index:
                wrong_word = content.paronyms[content.secondary_number - 1].inflected_form
                sentence = content.sentence.format(word=f"<b>{wrong_word.upper()}</b>")
            else:
                if not exercise.answer.isdigit():
                    msg = f"Exercise answer must be a digit (exercise {exercise.id})"
                    raise ValueError(msg)
                correct_answer_index = int(exercise.answer) - 1
                correct_word = content.paronyms[correct_answer_index].inflected_form
                sentence = content.sentence.format(word=f"<b>{correct_word.upper()}</b>")

            sentences.append(sentence)

        task_text = (
            "В одном из приведённых ниже предложений <b>НЕВЕРНО</b> употреблено выделенное слово. "
            "Исправьте лексическую ошибку, <b>подобрав к выделенному слову пароним</b>. Запишите подобранное слово, "
            "соблюдая нормы современного русского литературного языка.\n\n\n"
        )
        for i, sentence in enumerate(sentences, start=1):
            task_text += f"{i}) {sentence}\n"

        exercise_ids = [ex.id for ex in exercises]
        return TaskResponse(
            task_ui=TaskUI(
                text=task_text,
                options=None,
            ),
            exercise_ids=exercise_ids,
            task_config=Task5ExamConfig(
                exercise_ids=exercise_ids,
                wrong_sentence_index=wrong_sentence_index,
            ),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_SENTENCES_COUNT:
            msg = "User must have exactly 5 current exercises for TASK_5_EXAM"
            raise ValueError(msg)

        if user.current_task_config is None:
            msg = "Task config is required for TASK_5_EXAM"
            raise ValueError(msg)

        config = Task5ExamConfig.model_validate(user.current_task_config)

        exercises_map = {ex.id: ex for ex in user.current_exercises}
        ordered_exercises = [exercises_map[ex_id] for ex_id in config.exercise_ids]

        wrong_exercise = ordered_exercises[config.wrong_sentence_index]
        wrong_exercise_content = Task5Content.model_validate(wrong_exercise.content)

        if not wrong_exercise.answer.isdigit():
            msg = f"Exercise answer must be a digit (exercise {wrong_exercise.id})"
            raise ValueError(msg)
        correct_answer_index = int(wrong_exercise.answer) - 1

        correct_word = wrong_exercise_content.paronyms[correct_answer_index].inflected_form
        wrong_word = wrong_exercise_content.paronyms[wrong_exercise_content.secondary_number - 1].inflected_form

        is_correct = check_answer(
            user_answer,
            correct_word,
            allow_dash_variations=False,
            allow_space_omission=False,
        )

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        group_id = uuid.uuid4()

        for i, exercise in enumerate(ordered_exercises):
            exercise_is_correct = is_correct if i == config.wrong_sentence_index else True

            answer = UserAnswer(
                is_correct=exercise_is_correct,
                user_response=user_answer,
                solve_time=solve_time,
                group_id=group_id,
                user_id=user.id,
                exercise_id=exercise.id,
                category_id=user.current_category_id,
            )
            self._answer_repository.add(answer)

        word_text = correct_word.lower()
        if wrong_exercise_content.sentence.lstrip().startswith("{word}"):
            word_text = word_text.capitalize()
        sentence_with_correct_word = wrong_exercise_content.sentence.format(
            word=f"<u>{word_text}</u>",
        )

        paronym_explanations = "\n\n".join(
            paronym.explanation for paronym in wrong_exercise_content.paronyms
        )

        explanation = f"{sentence_with_correct_word}\n\n"
        if not is_correct:
            explanation += f"<b>Ваш ответ: {html.escape(user_answer, quote=False)}</b>\n"
            explanation += f"<b>Правильный ответ: {correct_word}</b>\n"
            explanation += f"<b>Неправильное слово в задании: {wrong_word}</b>\n\n"
        else:
            explanation += f"<b>Ответ: {correct_word}</b>\n"
            explanation += f"<b>Неправильное слово в задании: {wrong_word}</b>\n\n"

        explanation += paronym_explanations

        return CheckResult(
            is_correct=is_correct,
            explanation=explanation,
        )
