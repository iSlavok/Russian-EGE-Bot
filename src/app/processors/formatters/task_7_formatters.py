"""Форматтер задания 7 (морфологические нормы: форма слова): exam + drill.

Exam: 5 словосочетаний нумерованным списком в цитате, выделенное слово <b>ЗАГЛ</b>; разбор —
верх + разделитель + исправленное словосочетание в цитате + свёрнутый «Объяснение»
(открыт при неверном) + всегда свёрнутый «Словосочетания».
Drill: 2 кнопки; разбор — верх + разделитель + исправленное словосочетание + объяснение инлайн.
Логики выбора/проверки здесь нет — только view-model.
"""
from app.processors.formatters.base_formatter import BaseFormatter
from app.schemas import Collapsible, Divider, NumberedList, Paragraph, Quote, ResultView, TaskView


class Task7Formatter(BaseFormatter):
    TASK_NUMBER = 7
    EXAM_INSTRUCTION = (
        "В одном из выделенных ниже слов допущена грамматическая ошибка. "
        "Исправьте ошибку и запишите слово правильно."
    )
    DRILL_INSTRUCTION = "Выберите словосочетание, в котором нет грамматической ошибки."

    def condition(self, shown: list[tuple[str, str]]) -> TaskView:
        items = [self._bold_word_phrase(template, word) for template, word in shown]
        return TaskView(
            heading=self.heading,
            instruction=self.EXAM_INSTRUCTION,
            blocks=[NumberedList(items=items, quoted=True, paren=True)],
        )

    def result(
        self,
        *,
        correct_word: str,
        phrase_template: str,
        explanation: str,
        shown: list[tuple[str, str]],
        user_answer: str,
        is_correct: bool,
    ) -> ResultView:
        phrases = [self._bold_word_phrase(template, word) for template, word in shown]
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_word)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=[
                Divider(),
                Quote(lines=[self._corrected_phrase(phrase_template, correct_word)]),
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=explanation.replace("\n", "\n\n"))],
                    open_if_wrong=True,
                ),
                Collapsible(summary="Словосочетания", blocks=[NumberedList(items=phrases, quoted=True, paren=True)]),
            ],
        )

    def drill_condition(self) -> TaskView:
        return TaskView(heading=self.heading, instruction=self.DRILL_INSTRUCTION)

    def drill_result(
        self,
        *,
        correct_word: str,
        phrase_template: str,
        explanation: str,
        user_answer: str,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_word)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=[
                Divider(),
                Quote(lines=[self._corrected_phrase(phrase_template, correct_word)]),
                Paragraph(text=explanation),
            ],
        )

    def _bold_word_phrase(self, template: str, word: str) -> str:
        """Словосочетание с выделенным словом <b>ЗАГЛАВНЫМИ</b> (шаблон — как есть, слово экранируется)."""
        return template.format(word=f"<b>{self._esc(word.upper())}</b>")

    def _corrected_phrase(self, template: str, correct_word: str) -> str:
        """Словосочетание с верным словом <u><b>подчёркнутым+жирным</b></u> (с заглавной, если в начале)."""
        word = correct_word
        if template.lstrip().startswith("{word}"):
            word = word.capitalize()
        return template.format(word=f"<u><b>{self._esc(word)}</b></u>")
