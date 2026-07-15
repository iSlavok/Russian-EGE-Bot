"""Форматтер задания 1 (подбор слова на место пропуска).

Собирает view-model из сырых данных процессора. Логики проверки здесь нет.
"""
from app.processors.formatters.base_formatter import BaseFormatter
from app.processors.schemas import Task1Content
from app.schemas import ResultView, TaskView


class Task1Formatter(BaseFormatter):
    TASK_NUMBER = 1

    def condition(self, content: Task1Content) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=self._esc(content.instruction),
            blocks=[self._text_quote(content.text)],
        )

    def result(
        self,
        content: Task1Content,
        correct_answers: list[str],
        user_answer: str,
        *,
        is_correct: bool,
    ) -> ResultView:
        stripped = user_answer.strip()
        inserted = stripped if is_correct else correct_answers[0]
        return ResultView(
            correct=is_correct,
            answer=self._answer_line(correct_answers, stripped, is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(stripped),
            blocks=[self._gap_fragment(content.text, inserted)],
        )
