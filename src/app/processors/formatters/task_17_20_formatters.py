"""Форматтер заданий 17–20 (расстановка запятых, общий процессор, только exam).

Один форматтер на 4 задания — номер задаётся при инстанцировании (heading «Задание N»).
Условие: формулировка + предложение с (1)(2)… в цитате.
Разбор: ответ + предложение с запятыми в цитате + свёрнутый «Объяснение» (открыт при неверном).
Логики проверки здесь нет — только view-model.
"""
from app.processors.formatters.base_formatter import BaseFormatter
from app.schemas import Collapsible, Paragraph, Quote, ResultView, TaskView

_HARD_BREAK = "  \n"  # внутри <details> одиночный \n схлопывается
_FORMULATION = (
    "Расставьте все знаки препинания: укажите цифру(-ы), на месте которой(-ых) "
    "в предложении должна(-ы) стоять запятая(-ые)."
)


class TaskN17N20Formatter(BaseFormatter):
    def __init__(self, task_number: int) -> None:
        self.TASK_NUMBER = task_number

    def condition(self, sentence: str) -> TaskView:
        return TaskView(heading=self.heading, instruction=_FORMULATION, blocks=[self._text_quote(sentence)])

    def result(
        self,
        *,
        correct_answer: str,
        user_answer: str,
        correct_sentence: str,
        explanation: str,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_answer)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer or "—"), strike=True),
            blocks=[
                Quote(lines=[self._esc(correct_sentence)]),
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=explanation.strip().replace("\n", _HARD_BREAK))],
                    open_if_wrong=True,
                ),
            ],
        )
