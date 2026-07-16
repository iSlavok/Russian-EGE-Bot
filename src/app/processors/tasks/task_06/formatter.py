"""Форматтер задания 6 (лексические нормы: REMOVE — лишнее слово / REPLACE — замена).

Условие: инструкция по типу задания + предложение в цитате.
Разбор: верх (ответ юзера подсвечен в списке верных) + свёрнутый «Объяснение» (открыт при неверном)
+ свёрнутый «Предложение» (Исходное с ошибкой <s> / Правильное с заменой <u><b>).
Логики проверки здесь нет — только view-model.
"""
from app.processors._base.base_formatter import BaseFormatter
from app.schemas import Collapsible, Paragraph, Quote, ResultView, TaskView

from .schemas import Task6Content, Task6Type

_INSTRUCTIONS = {
    Task6Type.REMOVE: "Отредактируйте предложение: исправьте лексическую ошибку, <b>исключив лишнее слово.</b> "
                      "Выпишите это слово.",
    Task6Type.REPLACE: "Отредактируйте предложение: исправьте лексическую ошибку, "
                       "<b>заменив употреблённое неверно слово.</b> Запишите подобранное слово, соблюдая нормы "
                       "современного русского литературного языка и сохраняя смысл высказывания.",
}


class Task6Formatter(BaseFormatter):
    TASK_NUMBER = 6

    def condition(self, content: Task6Content) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=_INSTRUCTIONS[content.task_type],
            blocks=[self._text_quote(content.sentence)],
        )

    def result(
        self,
        content: Task6Content,
        correct_answers: list[str],
        user_answer: str,
        explanation: str,
        *,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(answer) for answer in correct_answers], user_answer,
                                     is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=[
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=explanation.replace("\n", "\n\n"))],
                    open_if_wrong=True,
                ),
                self._sentence_block(content),
            ],
        )

    @staticmethod
    def _sentence_block(content: Task6Content) -> Collapsible:
        """Свёрнутый «Предложение»: Исходное (ошибка <s>) / Правильное (замена <u><b>), оба в цитате."""
        error = content.sentence_with_markup.replace("<u>", "<s>").replace("</u>", "</s>")
        fix = content.corrected_sentence.replace("<u>", "<u><b>").replace("</u>", "</b></u>")
        return Collapsible(
            summary="Предложение",
            blocks=[
                Paragraph(text="**Исходное:**"),
                Quote(lines=[error]),
                Paragraph(text="**Правильное:**"),
                Quote(lines=[fix]),
            ],
        )
