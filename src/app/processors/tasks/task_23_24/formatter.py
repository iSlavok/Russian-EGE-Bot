"""Форматтер заданий 23–24 (утверждения о тексте, общий процессор, только exam).

Один форматтер на 2 задания — номер задаётся при инстанцировании (heading + формулировки + подпись
списка зависят от номера). Режим (верные/неверные утверждения) выбирает процессор.
Условие: формулировка + текст в <details open> (цитата) + список утверждений.
Разбор: ответ + 3 свёрнутых блока — «Объяснение» (открыт при неверном), список утверждений, «Текст».
Логики проверки здесь нет — только view-model.
"""
from app.processors._base.base_formatter import BaseFormatter
from app.schemas import Collapsible, NumberedList, Paragraph, ResultView, TaskView

_HARD_BREAK = "  \n"  # внутри <details> одиночный \n схлопывается

_CORRECT_FORMULATION = {
    23: "Какие из высказываний соответствуют содержанию текста? Укажите номера ответов.",
    24: "Какие из перечисленных утверждения являются верными? Укажите номера ответов.",
}
_INCORRECT_FORMULATION = {
    23: "Какие из высказываний <b>не соответствуют</b> содержанию текста? Укажите номера ответов.",
    24: "Какие из перечисленных утверждения являются <b>ошибочными</b>? Укажите номера ответов.",
}
_OPTIONS_LABEL = {23: "Высказывания", 24: "Утверждения"}


class Task2324Formatter(BaseFormatter):
    def __init__(self, task_number: int) -> None:
        self.TASK_NUMBER = task_number

    def condition(self, *, ask_incorrect: bool, text: str, options: list[str]) -> TaskView:
        formulation = (_INCORRECT_FORMULATION if ask_incorrect else _CORRECT_FORMULATION)[self.TASK_NUMBER]
        return TaskView(
            heading=self.heading,
            instruction=formulation,
            blocks=[
                Collapsible(summary="Текст", blocks=[self._text_quote(text)], open=True),
                Paragraph(text=f"**{_OPTIONS_LABEL[self.TASK_NUMBER]}:**"),
                self._options_list(options),
            ],
        )

    def result(
        self,
        *,
        correct_answer: str,
        user_answer: str,
        text: str,
        options: list[str],
        explanation: str,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_answer)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=[
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=explanation.strip().replace("\n", _HARD_BREAK))],
                    open_if_wrong=True,
                ),
                Collapsible(summary=_OPTIONS_LABEL[self.TASK_NUMBER], blocks=[self._options_list(options)]),
                Collapsible(summary="Текст", blocks=[self._text_quote(text)]),
            ],
        )

    def _options_list(self, options: list[str]) -> NumberedList:
        return NumberedList(items=[self._esc(option) for option in options])
