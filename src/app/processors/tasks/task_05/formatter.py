"""Форматтер задания 5 (паронимы): exam (5 предложений) и drill (1 с пропуском, кнопки).

Exam: предложения нумерованным списком в цитате, выделенное слово <b>ЗАГЛАВНЫМИ</b>; разбор —
верх + «Неправильное слово» + исправленное предложение в цитате + свёрнутый «Объяснение»
(открыт при неверном) + всегда свёрнутый «Предложения».
Drill: предложение с пропуском в цитате, паронимы на кнопках; разбор — верх + исправл. + «Объяснение».
Логики выбора/проверки здесь нет — только view-model.
"""
from app.processors._base.base_formatter import BaseFormatter
from app.schemas import AnswerLine, Collapsible, NumberedList, Paragraph, Quote, ResultView, TaskView


class Task5Formatter(BaseFormatter):
    TASK_NUMBER = 5
    EXAM_INSTRUCTION = (
        "В одном из приведённых ниже предложений <b>НЕВЕРНО</b> употреблено выделенное слово. "
        "Исправьте лексическую ошибку, <b>подобрав к выделенному слову пароним</b>. Запишите подобранное "
        "слово, соблюдая нормы современного русского литературного языка."
    )
    DRILL_INSTRUCTION = "В предложении пропущено слово. Выберите из предложенных паронимов подходящее по смыслу."

    def condition(self, shown: list[tuple[str, str]]) -> TaskView:
        items = [self._bold_word_sentence(template, word) for template, word in shown]
        return TaskView(
            heading=self.heading,
            instruction=self.EXAM_INSTRUCTION,
            blocks=[NumberedList(items=items, quoted=True, paren=True)],
        )

    def result(
        self,
        *,
        correct_word: str,
        wrong_word: str,
        sentence_template: str,
        paronym_explanations: list[str],
        shown: list[tuple[str, str]],
        user_answer: str,
        is_correct: bool,
    ) -> ResultView:
        sentences = [self._bold_word_sentence(template, word) for template, word in shown]
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_word)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            note=AnswerLine(label="Неправильное слово в задании", values=[self._esc(wrong_word)]),
            blocks=[
                Quote(lines=[self._corrected_sentence(sentence_template, correct_word)]),
                self._explanation_block(paronym_explanations),
                Collapsible(summary="Предложения", blocks=[NumberedList(items=sentences, paren=True)]),
            ],
        )

    def drill_condition(self, sentence_template: str) -> TaskView:
        sentence = sentence_template.format(word=self._esc(self.GAP))
        return TaskView(
            heading=self.heading,
            instruction=self.DRILL_INSTRUCTION,
            blocks=[Quote(lines=[sentence])],
        )

    def drill_result(
        self,
        *,
        correct_word: str,
        sentence_template: str,
        paronym_explanations: list[str],
        user_answer: str,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_word)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=[
                Quote(lines=[self._corrected_sentence(sentence_template, correct_word)]),
                self._explanation_block(paronym_explanations),
            ],
        )

    def _bold_word_sentence(self, template: str, word: str) -> str:
        """Предложение с выделенным словом <b>ЗАГЛАВНЫМИ</b> (шаблон — как есть, слово экранируется)."""
        return template.format(word=f"<b>{self._esc(word.upper())}</b>")

    def _corrected_sentence(self, template: str, correct_word: str) -> str:
        """Предложение с верным словом <u>подчёркнутым</u> (с заглавной, если слово в начале)."""
        word = correct_word.lower()
        if template.lstrip().startswith("{word}"):
            word = word.capitalize()
        return template.format(word=f"<u>{self._esc(word)}</u>")

    @staticmethod
    def _explanation_block(paronym_explanations: list[str]) -> Collapsible:
        """Свёрнутый блок «Объяснение» (открыт при неверном) — словарные статьи паронимов."""
        return Collapsible(
            summary="Объяснение",
            blocks=[Paragraph(text=explanation) for explanation in paronym_explanations],
            open_if_wrong=True,
        )
