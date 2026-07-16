"""Форматтер задания 15 (Н/НН): exam + drill.

Exam: одно предложение с пропусками (1)(2)…; разбор = ответ + исправленное предложение в цитате
+ свёрнутый «Объяснение» (открыт при неверном).
Drill: предложение с пропуском {n}, 2 кнопки (слово с Н / с НН); разбор без блока — буква <u>подчёркнута</u>
в слове «Ответ:», исправленное предложение, объяснение.
Логики выбора/проверки здесь нет — только view-model.
"""
from app.processors._base.base_formatter import BaseFormatter
from app.schemas import Block, Collapsible, Paragraph, Quote, ResultView, TaskView

_HARD_BREAK = "  \n"  # внутри <details> одиночный \n схлопывается
_DISPLAY = {"н": "Н", "нн": "НН"}
_FORMULATION = {"Н": "одна буква Н", "НН": "НН"}


class Task15Formatter(BaseFormatter):
    TASK_NUMBER = 15

    def condition(self, *, mode: str, sentence: str) -> TaskView:
        instruction = f"Укажите все цифру(-ы), на месте которой(-ых) пишется **{_FORMULATION[mode]}**."
        return TaskView(heading=self.heading, instruction=instruction, blocks=[self._text_quote(sentence)])

    def result(
        self,
        *,
        correct_answer: str,
        user_answer: str,
        corrected_sentence: str,
        explanation: str,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_answer)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=[
                Quote(lines=[corrected_sentence]),
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=explanation.strip().replace("\n", _HARD_BREAK))],
                    open_if_wrong=True,
                ),
            ],
        )

    def drill_condition(self, *, sentence: str) -> TaskView:
        gapped = self._esc(sentence).format(n="**(н/нн)**")
        return TaskView(
            heading=self.heading,
            instruction="Вставьте пропущенные буквы.",
            blocks=[Quote(lines=[gapped])],
        )

    def drill_result(
        self,
        *,
        word: str,
        sentence: str,
        answer: str,
        user_answer: str,
        explanation: str,
        is_correct: bool,
    ) -> ResultView:
        correct_word = word.format(n=f"<u>{_DISPLAY.get(answer, answer.upper())}</u>")
        wrong_line = None
        if not is_correct:
            user_word = word.format(n=f"<u>{_DISPLAY.get(user_answer, user_answer.upper())}</u>")
            wrong_line = self._your_answer_line(user_word, strike=True)
        blocks: list[Block] = [Quote(lines=[sentence.format(n=f"<u>{answer}</u>")])]
        if explanation.strip():
            blocks.append(Paragraph(text=explanation.strip()))
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([correct_word], "", is_correct=is_correct),
            wrong_answer=wrong_line,
            blocks=blocks,
        )
