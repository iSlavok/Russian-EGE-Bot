"""Форматтер задания 26 (средства связи предложений, только exam).

Структура как №25, но ответ — одна строка цифр (без вариантов-форм).
Условие: формулировка + фрагмент текста в <details open> (цитата).
Разбор: ответ + свёрнутый «Объяснение» (открыт при неверном) + свёрнутый «Фрагмент текста».
Логики проверки здесь нет — только view-model.
"""
from app.processors._base.base_formatter import BaseFormatter
from app.schemas import Collapsible, Paragraph, ResultView, TaskView

_HARD_BREAK = "  \n"  # внутри <details> одиночный \n схлопывается


class Task26Formatter(BaseFormatter):
    TASK_NUMBER = 26

    def condition(self, *, task: str, sentences: str) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=self._esc(task),
            blocks=[Collapsible(summary="Фрагмент текста", blocks=[self._text_quote(sentences)], open=True)],
        )

    def result(
        self,
        *,
        correct_answer: str,
        user_answer: str,
        sentences: str,
        explanation: str,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_answer)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer or "—"), strike=True),
            blocks=[
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=explanation.strip().replace("\n", _HARD_BREAK))],
                    open_if_wrong=True,
                ),
                Collapsible(summary="Фрагмент текста", blocks=[self._text_quote(sentences)]),
            ],
        )
