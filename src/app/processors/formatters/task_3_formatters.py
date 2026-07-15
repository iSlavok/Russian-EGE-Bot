"""Форматтер задания 3 (стилистический анализ фрагмента текста).

Условие: длинный текст в сворачиваемом (но развёрнутом) блоке + 5 утверждений.
Разбор: поле `explanation` показываем как есть, без парсинга.
Логики проверки здесь нет — собирается только view-model.
"""
from app.processors.formatters.base_formatter import BaseFormatter
from app.processors.schemas import Task3Content
from app.schemas import Collapsible, NumberedList, Paragraph, ResultView, TaskView


class Task3Formatter(BaseFormatter):
    TASK_NUMBER = 3
    INSTRUCTION = (
        "Укажите варианты ответов, в которых даны верные характеристики фрагмента текста. "
        "Запишите номера ответов."
    )

    def condition(self, content: Task3Content) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=self.INSTRUCTION,
            blocks=[
                Collapsible(summary="Текст", blocks=[self._text_quote(content.text)], open=True),
                self._statements(content.statements),
            ],
        )

    def result(
        self,
        content: Task3Content,
        correct_answer: str,
        explanation: str,
        user_answer: str,
        *,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([correct_answer], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(user_answer, strike=False),
            blocks=[
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=self._esc(explanation).replace("\n", "\n\n"))],
                    open_if_wrong=True,
                ),
                Collapsible(summary="Текст", blocks=[self._text_quote(content.text)]),
                Collapsible(summary="Варианты ответов", blocks=[self._statements(content.statements)]),
            ],
        )

    def _statements(self, statements: list[str]) -> NumberedList:
        return NumberedList(items=[self._esc(stmt) for stmt in statements])
