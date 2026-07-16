"""Форматтер задания 21 (пунктуационный анализ): exam + drill.

Тип знака (COMMA/DASH/COLON) определяет формулировку и набор правил-кнопок — все дисплей-подписи
живут здесь. Exam: длинный текст в <details open> с цитатой; разбор — ответ + «Объяснение» + «Текст».
Drill: 1 предложение + кнопки-правила; разбор — правило + предложение в цитате + «Объяснение».
Логики выбора/проверки здесь нет — только view-model.
"""
from app.processors.formatters.base_formatter import BaseFormatter
from app.processors.schemas.task_21_schemas import (
    Task21ColonRule,
    Task21CommaRule,
    Task21DashRule,
    Task21TaskType,
)
from app.schemas import Collapsible, Paragraph, ResultView, TaskOption, TaskView

_HARD_BREAK = "  \n"  # внутри <details> одиночный \n схлопывается

_DRILL_OPTIONS_PER_ROW: dict[Task21TaskType, int | list[int]] = {
    Task21TaskType.COMMA: [1, 1, 1, 1, 2, 2, 2, 2, 2],
    Task21TaskType.DASH: [1, 1, 1, 1, 2, 2],
    Task21TaskType.COLON: [1, 2],
}

_DRILL_FORMULATION: dict[Task21TaskType, str] = {
    Task21TaskType.COMMA: "По какому правилу в этом предложении ставится запятая?",
    Task21TaskType.DASH: "По какому правилу в этом предложении ставится тире?",
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
    Task21CommaRule.MODIFIER: "Обособленное определение",
    Task21CommaRule.ADVERBIAL: "Обособленное обстоятельство",
    Task21CommaRule.SUPPLEMENT: "Обособленное дополнение",
    Task21CommaRule.COMPARISON: "Сравнительный оборот",
    Task21CommaRule.HOMOGENEOUS: "Однородные члены",
    Task21CommaRule.APPOSITION: "Приложение",
    Task21CommaRule.CLARIFICATION: "Уточнение",
    Task21CommaRule.SSP: "ССП",
    Task21CommaRule.SPP: "СПП",
    Task21CommaRule.BSP: "БСП",
    Task21CommaRule.VOCATIVE: "Обращение",
    Task21CommaRule.PARENTHETICAL: "Вводные слова",
    Task21CommaRule.INTERJECTION: "Междометие",
    Task21CommaRule.DIRECT_SPEECH: "Прямая речь",
}

_DASH_RULE_NAMES: dict[Task21DashRule, str] = {
    Task21DashRule.SUBJ_PRED: "Подлежащее и сказуемое",
    Task21DashRule.INCOMPLETE: "Неполное предложение",
    Task21DashRule.INSERTION: "Вставная конструкция",
    Task21DashRule.HOMOGENEOUS: "Однородные члены",
    Task21DashRule.DIRECT_SPEECH: "Прямая речь",
    Task21DashRule.APPOSITION: "Приложение",
    Task21DashRule.CLARIFICATION: "Уточнение",
    Task21DashRule.BSP: "БСП",
}

_COLON_RULE_NAMES: dict[Task21ColonRule, str] = {
    Task21ColonRule.HOMOGENEOUS: "Однородные члены",
    Task21ColonRule.BSP: "БСП",
    Task21ColonRule.DIRECT_SPEECH: "Прямая речь",
}

_RULE_NAMES_BY_TYPE: dict[Task21TaskType, dict] = {
    Task21TaskType.COMMA: _COMMA_RULE_NAMES,
    Task21TaskType.DASH: _DASH_RULE_NAMES,
    Task21TaskType.COLON: _COLON_RULE_NAMES,
}


def _rule_name(task_type: Task21TaskType, rule: str) -> str:
    return _RULE_NAMES_BY_TYPE[task_type].get(rule, rule)


class Task21Formatter(BaseFormatter):
    TASK_NUMBER = 21

    def condition(self, *, task_type: Task21TaskType, full_text: str) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=_EXAM_FORMULATION[task_type],
            blocks=[Collapsible(summary="Текст", blocks=[self._text_quote(full_text)], open=True)],
        )

    def result(
        self,
        *,
        task_type: Task21TaskType,
        answer: str,
        answer_rule: str,
        user_answer: str,
        full_text: str,
        explanation: str,
        is_correct: bool,
    ) -> ResultView:
        rule = _rule_name(task_type, answer_rule)
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([f"{self._esc(answer)} — {self._esc(rule)}"], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer or "—"), strike=True),
            blocks=[
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=explanation.strip().replace("\n", _HARD_BREAK))],
                    open_if_wrong=True,
                ),
                Collapsible(summary="Текст", blocks=[self._text_quote(full_text)]),
            ],
        )

    def drill_condition(self, *, task_type: Task21TaskType, text: str) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=_DRILL_FORMULATION[task_type],
            blocks=[self._text_quote(text)],
        )

    def drill_result(
        self,
        *,
        task_type: Task21TaskType,
        answer: str,
        user_answer: str,
        text: str,
        explanation: str,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(_rule_name(task_type, answer))], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(
                self._esc(_rule_name(task_type, user_answer)), strike=True),
            blocks=[
                self._text_quote(text),
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=explanation.strip())],
                    open_if_wrong=True,
                ),
            ],
        )

    @staticmethod
    def drill_options(task_type: Task21TaskType) -> list[TaskOption]:
        return [TaskOption(text=name, value=rule.value) for rule, name in _RULE_NAMES_BY_TYPE[task_type].items()]

    @staticmethod
    def drill_options_per_row(task_type: Task21TaskType) -> int | list[int]:
        return _DRILL_OPTIONS_PER_ROW[task_type]
