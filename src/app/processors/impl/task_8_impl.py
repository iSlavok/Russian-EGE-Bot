import random
import uuid
from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task8Content, Task8ExamConfig
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

EXAM_ERROR_COUNT = 5
EXAM_CORRECT_COUNT = 4
EXAM_TOTAL_COUNT = EXAM_ERROR_COUNT + EXAM_CORRECT_COUNT

NO_ERROR_ANSWER = "no_error"

ERROR_TYPE_DESCRIPTIONS: dict[str, str] = {
    "participial_clause_error": "нарушение в построении предложения с причастным оборотом",
    "homogeneous_members_error": "ошибка в построении предложения с однородными членами",
    "adverbial_participle_error": "неправильное построение предложения с деепричастным оборотом",
    "prepositional_case_error": "неправильное употребление падежной формы существительного с предлогом",
    "subject_predicate_agreement": "нарушение связи между подлежащим и сказуемым",
    "mismatched_appositive_error": "нарушение в построении предложения с несогласованным приложением",
    "complex_sentence_error": "ошибка в построении сложного предложения",
    "indirect_speech_error": "неправильное построение предложения с косвенной речью",
    "verb_aspect_tense_error": "нарушение видо-временной соотнесённости глагольных форм",
    "numeral_usage_error": "неправильное употребление имени числительного",
}

ERROR_TYPE_SHORT_LABELS: dict[str, str] = {
    "participial_clause_error": "Причастный оборот",
    "homogeneous_members_error": "Однородные члены",
    "adverbial_participle_error": "Деепричастный оборот",
    "prepositional_case_error": "Падеж с предлогом",
    "subject_predicate_agreement": "Подлежащее и сказуемое",
    "mismatched_appositive_error": "Несогл. приложение",
    "complex_sentence_error": "Сложное предложение",
    "indirect_speech_error": "Косвенная речь",
    "verb_aspect_tense_error": "Видо-время глаголов",
    "numeral_usage_error": "Числительное",
}

LETTER_LABELS = ["А", "Б", "В", "Г", "Д"]


class Task8DrillProcessor(BaseTaskProcessor):
    """Процессор для тренировочного режима задания 8.

    Показывает одно предложение с ошибкой и 10 кнопок с типами ошибок.
    Пользователь должен определить тип грамматической ошибки.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category for Task 8"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random_with_content_filter(
            category_id=user.current_category.parent_id,
            content_field="corrected_sentence",
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task8Content.model_validate(exercise.content)

        options = [
            TaskOption(text=label, value=error_type)
            for error_type, label in ERROR_TYPE_SHORT_LABELS.items()
        ]

        task_text = (
            "<b>Определите тип грамматической ошибки в предложении.</b>\n\n"
            f"<i>{content.sentence}</i>"
        )

        return TaskResponse(
            task_ui=TaskUI(
                text=task_text,
                options=options,
            ),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises to check answer for"
            raise ValueError(msg)
        exercise = user.current_exercises[0]

        is_correct = user_answer == exercise.answer

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        answer = UserAnswer(
            is_correct=is_correct,
            user_response=user_answer,
            solve_time=solve_time,
            user_id=user.id,
            exercise_id=exercise.id,
            category_id=user.current_category_id,
        )
        self._answer_repository.add(answer)

        content = Task8Content.model_validate(exercise.content)
        correct_label = ERROR_TYPE_SHORT_LABELS.get(exercise.answer, exercise.answer)

        explanation_parts = []
        if is_correct:
            explanation_parts.append(f"<b>Ответ:</b> {correct_label}")
        else:
            user_label = ERROR_TYPE_SHORT_LABELS.get(user_answer, user_answer)
            explanation_parts.append(f"<b>Ваш ответ:</b> {user_label}")
            explanation_parts.append(f"<b>Правильный ответ:</b> {correct_label}")

        explanation_parts.append(f"\n<b>Исходное предложение:</b>\n<i>{content.sentence}</i>")
        if content.corrected_sentence:
            explanation_parts.append(f"\n<b>Правильное предложение:</b>\n<i>{content.corrected_sentence}</i>")
        if exercise.explanation:
            explanation_parts.append(f"\n<b>Объяснение:</b>\n{exercise.explanation}")

        return CheckResult(
            is_correct=is_correct,
            explanation="\n".join(explanation_parts),
        )


class Task8ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 8.

    Показывает 9 предложений (5 с ошибками + 4 без) и 5 типов ошибок (А-Д).
    Пользователь вводит 5 цифр — номера предложений для каждой буквы.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category for Task 8"
            raise ValueError(msg)

        parent_id = user.current_category.parent_id

        error_exercises = list(await self._exercise_repository.get_random_with_distinct_answer(
            category_id=parent_id,
            exclude_answer=NO_ERROR_ANSWER,
            limit=EXAM_ERROR_COUNT,
        ))
        if len(error_exercises) < EXAM_ERROR_COUNT:
            raise TaskForUserNotFoundError(user.id)

        correct_exercises = list(await self._exercise_repository.get_random_by_answer(
            category_id=parent_id,
            answer=NO_ERROR_ANSWER,
            limit=EXAM_CORRECT_COUNT,
        ))
        if len(correct_exercises) < EXAM_CORRECT_COUNT:
            raise TaskForUserNotFoundError(user.id)

        all_exercises = error_exercises + correct_exercises
        random.shuffle(all_exercises)

        error_type_order = [ex.answer for ex in error_exercises]
        random.shuffle(error_type_order)

        task_text = (
            "<b>Установите соответствие между грамматическими ошибками и предложениями, "
            "в которых они допущены: к каждой позиции первого столбца подберите "
            "соответствующую позицию из второго столбца.</b>\n\n"
            "<b>ГРАММАТИЧЕСКИЕ ОШИБКИ</b>\n"
        )
        for i, error_type in enumerate(error_type_order):
            description = ERROR_TYPE_DESCRIPTIONS.get(error_type, error_type)
            task_text += f"{LETTER_LABELS[i]}) {description}\n"

        task_text += "\n<b>ПРЕДЛОЖЕНИЯ</b>\n"
        for i, exercise in enumerate(all_exercises, start=1):
            content = Task8Content.model_validate(exercise.content)
            task_text += f"{i}) {content.sentence}\n"

        task_text += "\nЗапишите в ответ цифры, соответствующие буквам АБВГД."

        exercise_ids = [ex.id for ex in all_exercises]
        return TaskResponse(
            task_ui=TaskUI(
                text=task_text,
                options=None,
            ),
            exercise_ids=exercise_ids,
            task_config=Task8ExamConfig(
                exercise_ids=exercise_ids,
                error_type_order=error_type_order,
            ),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_TOTAL_COUNT:
            msg = f"User must have exactly {EXAM_TOTAL_COUNT} current exercises for TASK_8_EXAM"
            raise ValueError(msg)

        if user.current_task_config is None:
            msg = "Task config is required for TASK_8_EXAM"
            raise ValueError(msg)

        config = Task8ExamConfig.model_validate(user.current_task_config)

        exercises_map = {ex.id: ex for ex in user.current_exercises}
        ordered_exercises = [exercises_map[ex_id] for ex_id in config.exercise_ids]

        correct_answer = ""
        for error_type in config.error_type_order:
            for i, ex in enumerate(ordered_exercises, start=1):
                if ex.answer == error_type:
                    correct_answer += str(i)
                    break

        user_digits = "".join(c for c in user_answer if c.isdigit())
        is_correct = user_digits == correct_answer

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        group_id = uuid.uuid4()

        user_selected = {int(c) for c in user_digits if c.isdigit() and 1 <= int(c) <= EXAM_TOTAL_COUNT}

        explanation = ""
        for i, exercise in enumerate(ordered_exercises, start=1):
            content = Task8Content.model_validate(exercise.content)
            explanation += "<blockquote expandable>"
            if exercise.answer != NO_ERROR_ANSWER:
                error_idx = config.error_type_order.index(exercise.answer)
                letter = LETTER_LABELS[error_idx]
                word_correct = len(user_digits) > error_idx and user_digits[error_idx] == str(i)
                description = ERROR_TYPE_DESCRIPTIONS.get(exercise.answer, exercise.answer)

                explanation += f"<b>{i}) {letter} — {description}</b>\n"
                explanation += f"<b>Исходное предложение:</b> <i>{content.sentence}</i>\n"
                if content.corrected_sentence:
                    explanation += f"<b>Правильное предложение:</b> <i>{content.corrected_sentence}</i>\n"
                if exercise.explanation:
                    explanation += f"<b>Объяснение:</b> {exercise.explanation}\n\n"
            else:
                word_correct = i not in user_selected
                explanation += f"<b>{i}) Нет ошибки</b>\n"
                explanation += f"<b>Предложение:</b> <i>{content.sentence}</i>\n\n"

            explanation += "</blockquote>\n"

            user_answer_record = UserAnswer(
                is_correct=word_correct,
                user_response=user_answer,
                solve_time=solve_time,
                group_id=group_id,
                user_id=user.id,
                exercise_id=exercise.id,
                category_id=user.current_category_id,
            )
            self._answer_repository.add(user_answer_record)

        if is_correct:
            explanation = f"<b>Ответ: {correct_answer}</b>\n\n" + explanation
        else:
            explanation = (
                f"Ваш ответ: {user_digits}\n"
                f"<b>Правильный ответ: {correct_answer}</b>\n\n"
                + explanation
            )

        return CheckResult(
            is_correct=is_correct,
            explanation=explanation,
        )
