"""Форматтер задания 25 (лексический анализ, только exam).

Условие: формулировка + фрагмент текста в <details open> (цитата).
Разбор: ответ (формы слова через « / », форма юзера подчёркнута) + свёрнутый «Объяснение»
(открыт при неверном) + свёрнутый «Фрагмент текста».
Ответ — «одно слово» с несколькими допустимыми формами, поэтому метка «Ответ» единственная.
Логики проверки здесь нет — только view-model.
"""
from app.processors.formatters.base_formatter import BaseFormatter
from app.schemas import AnswerLine, Collapsible, Paragraph, ResultView, TaskView

_HARD_BREAK = "  \n"  # внутри <details> одиночный \n схлопывается


class Task25Formatter(BaseFormatter):
    TASK_NUMBER = 25

    def condition(self, *, task: str, sentences: str) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=self._esc(task),
            blocks=[Collapsible(summary="Фрагмент текста", blocks=[self._text_quote(sentences)], open=True)],
        )

    def result(
        self,
        *,
        forms: list[str],
        user_answer: str,
        sentences: str,
        explanation: str,
        is_correct: bool,
    ) -> ResultView:
        escaped_forms = [self._esc(form) for form in forms]
        if is_correct:
            answer = AnswerLine(label="Ответ", values=escaped_forms, user=self._esc(user_answer))
            wrong_line = None
        else:
            answer = AnswerLine(label="Правильный ответ", values=escaped_forms)
            wrong_line = self._your_answer_line(self._esc(user_answer), strike=True)
        return ResultView(
            correct=is_correct,
            answer=answer,
            wrong_answer=wrong_line,
            blocks=[
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=explanation.strip().replace("\n", _HARD_BREAK))],
                    open_if_wrong=True,
                ),
                Collapsible(summary="Фрагмент текста", blocks=[self._text_quote(sentences)]),
            ],
        )
