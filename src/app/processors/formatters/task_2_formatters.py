"""Форматтер задания 2 (лексическое значение слова в контексте).

Контент уже содержит HTML-разметку (<b>, <u>, <i>) — отдаём как есть, без экранирования.
Логики проверки здесь нет: собирается только view-model.
"""
from app.processors.formatters.base_formatter import BaseFormatter
from app.processors.schemas import Task2Content
from app.schemas import AnswerLine, Collapsible, Paragraph, Quote, ResultView, TaskView

_VERDICT = {"true": "Подходит", "false": "Не подходит"}


class Task2Formatter(BaseFormatter):
    TASK_NUMBER = 2
    INSTRUCTION = (
        "В предложении выделено слово. Определите, соответствует ли указанное "
        "лексическое значение его значению в данном контексте."
    )

    def condition(self, content: Task2Content) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=self.INSTRUCTION,
            blocks=[
                Quote(lines=content.text.split("\n")),
                Paragraph(text=content.word_with_definition),
            ],
        )

    def result(
        self,
        content: Task2Content,
        correct_answer: str,
        explanation: str | None,
        *,
        is_correct: bool,
    ) -> ResultView:
        note = None
        if correct_answer == "false" and explanation:
            note = AnswerLine(label="Верное значение", values=[explanation])
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([_VERDICT[correct_answer]], "", is_correct=is_correct),
            note=note,
            blocks=[
                Collapsible(summary="Фрагмент текста", blocks=[Quote(lines=content.text.split("\n"))]),
                Collapsible(summary="Значение из задания", blocks=[Paragraph(text=content.word_with_definition)]),
            ],
        )
