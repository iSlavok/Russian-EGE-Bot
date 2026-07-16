"""Форматтер задания 4 (ударение): exam (5 слов) и drill (1 слово, 2 кнопки).

Exam: слова нумерованным списком в цитате, ударная буква — ЗАГЛАВНАЯ; разбор — свёрнутый
блок «Объяснение» (открыт при неверном) со списком объяснений (raw HTML из БД).
Drill: инструкция с выделенным словом, варианты на кнопках; разбор — вердикт + объяснение инлайн.
Логики выбора/проверки здесь нет — только view-model.
"""
from app.processors._base.base_formatter import BaseFormatter
from app.schemas import Collapsible, NumberedList, Paragraph, ResultView, TaskView

from .schemas import Task4Content


class Task4Formatter(BaseFormatter):
    TASK_NUMBER = 4
    INSTRUCTION = (
        "Укажите варианты ответов, в которых верно выделена буква, обозначающая ударный гласный звук. "
        "Запишите номера ответов."
    )

    def condition(self, contents: list[Task4Content], stress_positions: list[int]) -> TaskView:
        items = [self._word_display(content, stress_positions[i]) for i, content in enumerate(contents)]
        return TaskView(
            heading=self.heading,
            instruction=self.INSTRUCTION,
            blocks=[NumberedList(items=items, quoted=True, paren=True)],
        )

    def result(
        self,
        explanations: list[str],
        correct_numbers: str,
        user_answer: str,
        *,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([correct_numbers], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(user_answer, strike=False),
            blocks=[
                Collapsible(
                    summary="Объяснение",
                    blocks=[NumberedList(items=explanations, paren=True)],
                    open_if_wrong=True,
                ),
            ],
        )

    def drill_condition(self, content: Task4Content) -> TaskView:
        phrase = self._with_context(self._esc(content.word), content)
        return TaskView(
            heading=self.heading,
            instruction=f"Выберите правильное ударение в слове: **{phrase}**.",
        )

    @staticmethod
    def drill_result(explanation: str, *, is_correct: bool) -> ResultView:
        return ResultView(correct=is_correct, blocks=[Paragraph(text=explanation)])

    def _word_display(self, content: Task4Content, stress_index: int) -> str:
        """Слово с ЗАГЛАВНОЙ ударной буквой (позиция 1-based) + опциональный контекст, экранировано."""
        i = stress_index - 1
        word = self._esc(content.word[:i] + content.word[i].upper() + content.word[i + 1:])
        return self._with_context(word, content)

    def _with_context(self, text: str, content: Task4Content) -> str:
        if content.context_before:
            text = f"{self._esc(content.context_before)} {text}"
        if content.context_after:
            text = f"{text} {self._esc(content.context_after)}"
        return text
