"""Форматтер заданий 9–12 (правописание, общий процессор): exam + drill.

Один форматтер на 4 задания — номер задания задаётся при инстанцировании (heading «Задание N»).
Exam условие: 5 рядов слов (пропуск ..) нумерованным списком в цитате.
Exam разбор: верх + блоки «Ряд N» (раскрыт тот, где юзер ошибся), внутри слова курсивом с <u><b>буквой</b></u>
+ объяснение, слова разделены `---`.
Drill: 1 слово + 2 кнопки; разбор без блока — буква подчёркнута прямо в «Ответ:», объяснение ниже.
Логики выбора/проверки здесь нет — только view-model.
"""
from dataclasses import dataclass

from app.processors.formatters.base_formatter import BaseFormatter
from app.schemas import Block, Collapsible, Divider, NumberedList, Paragraph, Quote, ResultView, TaskView

_HARD_BREAK = "  \n"  # внутри <details> одиночный \n схлопывается — жёсткий перенос без пустой строки


@dataclass(frozen=True)
class N9N12Word:
    """Слово ряда: шаблон с {letter}, верная буква, контекст, объяснение."""
    template: str
    answer_letter: str
    context_before: str | None
    context_after: str | None
    explanation: str


@dataclass(frozen=True)
class N9N12Row:
    """Ряд слов; `wrong` — ошибся ли юзер по этому ряду (для раскрытия блока в разборе)."""
    words: list[N9N12Word]
    wrong: bool = False


class TaskN9N12Formatter(BaseFormatter):
    EXAM_INSTRUCTION = (
        "Укажите варианты ответов, в которых во всех словах одного ряда пропущена одна и та же буква. "
        "Запишите номера ответов."
    )
    DRILL_INSTRUCTION = "Выберите правильный вариант ответа, вставив пропущенную букву в слово."

    def __init__(self, task_number: int) -> None:
        self.TASK_NUMBER = task_number

    def condition(self, rows: list[N9N12Row]) -> TaskView:
        items = [", ".join(self._gap(word) for word in row.words) for row in rows]
        return TaskView(
            heading=self.heading,
            instruction=self.EXAM_INSTRUCTION,
            blocks=[NumberedList(items=items, quoted=True, paren=True)],
        )

    def result(
        self,
        *,
        correct_answer: str,
        user_answer: str,
        rows: list[N9N12Row],
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_answer)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=[self._row_block(i, row) for i, row in enumerate(rows, start=1)],
        )

    def drill_condition(self, word: N9N12Word) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=self.DRILL_INSTRUCTION,
            blocks=[Quote(lines=[self._gap(word)])],
        )

    def drill_result(self, *, word: N9N12Word, user_letter: str, is_correct: bool) -> ResultView:
        filled = word.template.replace("{letter}", f"<u>{self._esc(word.answer_letter.upper())}</u>")
        wrong_line = None
        if not is_correct:
            user_filled = word.template.replace("{letter}", self._esc(user_letter.upper()))
            wrong_line = self._your_answer_line(user_filled, strike=True)
        blocks: list[Block] = [Paragraph(text=self._esc(word.explanation.strip()))] if word.explanation else []
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([filled], "", is_correct=is_correct),
            wrong_answer=wrong_line,
            blocks=blocks,
        )

    def _row_block(self, number: int, row: N9N12Row) -> Collapsible:
        blocks: list[Block] = []
        for index, word in enumerate(row.words):
            if index > 0:
                blocks.append(Divider())
            blocks.append(Paragraph(text=self._word_unit(word)))
        return Collapsible(summary=f"Ряд {number}", blocks=blocks, open=row.wrong)

    def _word_unit(self, word: N9N12Word) -> str:
        line = f"_{self._filled(word)}_"
        if word.explanation:
            line += f"{_HARD_BREAK}{self._esc(word.explanation.strip())}"
        return line

    def _gap(self, word: N9N12Word) -> str:
        return self._context(word.template.replace("{letter}", ".."), word)

    def _filled(self, word: N9N12Word) -> str:
        letter = f"<u><b>{self._esc(word.answer_letter.upper())}</b></u>"
        return self._context(word.template.replace("{letter}", letter), word)

    @staticmethod
    def _context(word_str: str, word: N9N12Word) -> str:
        parts = []
        if word.context_before:
            parts.append(word.context_before)
        parts.append(word_str)
        if word.context_after:
            parts.append(word.context_after)
        return " ".join(parts)
