from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas.task_21_schemas import (
    Task21ColonRule,
    Task21CommaRule,
    Task21DashRule,
    Task21DrillContent,
    Task21ExamContent,
    Task21TaskType,
)
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

DRILL_OPTIONS_PER_ROW: dict[Task21TaskType, int | list[int]] = {
    Task21TaskType.COMMA: [1, 1, 1, 1, 2, 2, 2, 2, 2],
    Task21TaskType.DASH:  [1, 1, 1, 1, 2, 2],
    Task21TaskType.COLON: [1, 2],
}

_DRILL_FORMULATION: dict[Task21TaskType, str] = {
    Task21TaskType.COMMA: "По какому правилу в этом предложении ставится запятая?",
    Task21TaskType.DASH:  "По какому правилу в этом предложении ставится тире?",
    Task21TaskType.COLON: "По какому правилу в этом предложении ставится двоеточие?",
}

_EXAM_FORMULATION: dict[Task21TaskType, str] = {
    Task21TaskType.COMMA: (
        "Найдите предложения, в которых запятая(-ые) ставится(-ятся) в соответствии с одним и тем же правилом "
        "пунктуации. Запишите номера этих предложений."
    ),
    Task21TaskType.DASH: (
        "Найдите предложения, в которых тире ставится в соответствии с одним и тем же правилом пунктуации. "
        "Запишите номера этих предложений."
    ),
    Task21TaskType.COLON: (
        "Найдите предложения, в которых двоеточие ставится в соответствии с одним и тем же правилом пунктуации. "
        "Запишите номера этих предложений."
    ),
}

_COMMA_RULE_NAMES: dict[Task21CommaRule, str] = {
    Task21CommaRule.MODIFIER:      "Обособленное определение",
    Task21CommaRule.ADVERBIAL:     "Обособленное обстоятельство",
    Task21CommaRule.SUPPLEMENT:    "Обособленное дополнение",
    Task21CommaRule.COMPARISON:    "Сравнительный оборот",
    Task21CommaRule.HOMOGENEOUS:   "Однородные члены",
    Task21CommaRule.APPOSITION:    "Приложение",
    Task21CommaRule.CLARIFICATION: "Уточнение",
    Task21CommaRule.SSP:           "ССП",
    Task21CommaRule.SPP:           "СПП",
    Task21CommaRule.BSP:           "БСП",
    Task21CommaRule.VOCATIVE:      "Обращение",
    Task21CommaRule.PARENTHETICAL: "Вводные слова",
    Task21CommaRule.INTERJECTION:  "Междометие",
    Task21CommaRule.DIRECT_SPEECH: "Прямая речь",
}

_DASH_RULE_NAMES: dict[Task21DashRule, str] = {
    Task21DashRule.SUBJ_PRED:     "Подлежащее и сказуемое",
    Task21DashRule.INCOMPLETE:    "Неполное предложение",
    Task21DashRule.INSERTION:     "Вставная конструкция",
    Task21DashRule.HOMOGENEOUS:   "Однородные члены",
    Task21DashRule.DIRECT_SPEECH: "Прямая речь",
    Task21DashRule.APPOSITION:    "Приложение",
    Task21DashRule.CLARIFICATION: "Уточнение",
    Task21DashRule.BSP:           "БСП",
}

_COLON_RULE_NAMES: dict[Task21ColonRule, str] = {
    Task21ColonRule.HOMOGENEOUS:   "Однородные члены",
    Task21ColonRule.BSP:           "БСП",
    Task21ColonRule.DIRECT_SPEECH: "Прямая речь",
}

_RULE_NAMES_BY_TYPE: dict[Task21TaskType, dict] = {
    Task21TaskType.COMMA: _COMMA_RULE_NAMES,
    Task21TaskType.DASH:  _DASH_RULE_NAMES,
    Task21TaskType.COLON: _COLON_RULE_NAMES,
}


def _rule_name(task_type: Task21TaskType, rule: str) -> str:
    return _RULE_NAMES_BY_TYPE[task_type].get(rule, rule)


class Task21DrillProcessor(BaseTaskProcessor):
    """Тренировочный режим задания 21.

    Показывает одно предложение. Кнопки — правила постановки знака.
    Ответ — одно правило (например, SUBJ_PRED).
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task21DrillContent.model_validate(exercise.content)
        rule_names = _RULE_NAMES_BY_TYPE[content.task_type]

        task_text = f"{_DRILL_FORMULATION[content.task_type]}\n\n<i>{content.text}</i>"
        options = [TaskOption(text=name, value=rule.value) for rule, name in rule_names.items()]

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=options, options_per_row=DRILL_OPTIONS_PER_ROW[content.task_type]),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises"
            raise ValueError(msg)
        exercise = user.current_exercises[0]

        is_correct = user_answer == exercise.answer

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

        content = Task21DrillContent.model_validate(exercise.content)
        correct_name = _rule_name(content.task_type, exercise.answer)

        if is_correct:
            explanation = f"<b>Ответ:</b> {correct_name}"
        else:
            user_name = _rule_name(content.task_type, user_answer)
            explanation = (
                f"<b>Ваш ответ:</b> {user_name}\n"
                f"<b>Правильный ответ:</b> {correct_name}"
            )

        explanation += f"\n\n<i>{content.text}</i>\n\n{exercise.explanation}"

        return CheckResult(is_correct=is_correct, explanation=explanation)


class Task21ExamProcessor(BaseTaskProcessor):
    """Экзаменационный режим задания 21.

    Показывает текст из нескольких пронумерованных предложений.
    Пользователь вводит номера предложений, где знак стоит по одному правилу.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task21ExamContent.model_validate(exercise.content)
        task_text = f"{_EXAM_FORMULATION[content.task_type]}\n\n<i>{content.full_text}</i>"

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=None),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises"
            raise ValueError(msg)
        exercise = user.current_exercises[0]

        user_digits = "".join(sorted(c for c in user_answer if c.isdigit()))
        is_correct = user_digits == exercise.answer

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

        content = Task21ExamContent.model_validate(exercise.content)
        rule_name = _rule_name(content.task_type, content.answer_rule)

        if is_correct:
            explanation = f"<b>Ответ:</b> {exercise.answer} — {rule_name}"
        else:
            explanation = (
                f"<b>Ваш ответ:</b> {user_digits or '—'}\n"
                f"<b>Правильный ответ:</b> {exercise.answer} — {rule_name}"
            )

        explanation += f"\n\n<b>Текст:</b>\n<blockquote expandable>{content.full_text}</blockquote>"

        explanation += f"\n\n<b>Объяснение:</b>\n<blockquote expandable>{exercise.explanation}</blockquote>"

        return CheckResult(is_correct=is_correct, explanation=explanation)
