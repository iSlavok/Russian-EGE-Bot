"""Форматтер задания 16 (пунктуация ССП/однородные члены): exam + drill.

Exam: 5 предложений без запятых; разбор — пер-предложенческие блоки (раскрыт тот, где юзер ошибся),
внутри исправленное предложение в цитате + объяснение.
Drill: 1 предложение, кнопки 0–7 (сколько запятых); разбор — ответ + исправленное предложение
+ свёрнутый «Объяснение» (открыт при неверном).
Логики выбора/проверки здесь нет — только view-model.
"""
from dataclasses import dataclass

from app.processors._base.base_formatter import BaseFormatter
from app.schemas import Block, Collapsible, NumberedList, Paragraph, Quote, ResultView, TaskView


@dataclass(frozen=True)
class Task16Sentence:
    """Предложение разбора: исправленное предложение, объяснение, ошибся ли юзер."""
    corrected_sentence: str
    explanation: str
    wrong: bool = False


class Task16Formatter(BaseFormatter):
    TASK_NUMBER = 16
    EXAM_INSTRUCTION = (
        "Укажите предложения, в которых нужно поставить **ОДНУ** запятую. Запишите номера этих предложений."
    )

    def condition(self, sentences: list[str]) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=self.EXAM_INSTRUCTION,
            blocks=[NumberedList(items=[self._esc(sentence) for sentence in sentences], quoted=True, paren=True)],
        )

    def result(
        self,
        *,
        correct_answer: str,
        user_answer: str,
        sentences: list[Task16Sentence],
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_answer)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=[self._sentence_block(i, sentence) for i, sentence in enumerate(sentences, start=1)],
        )

    def drill_condition(self, sentence: str) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction="Сколько запятых нужно поставить в предложении?",
            blocks=[self._text_quote(sentence)],
        )

    def drill_result(
        self,
        *,
        answer: str,
        user_answer: str,
        corrected_sentence: str,
        explanation: str,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(answer)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=[
                Quote(lines=[self._esc(corrected_sentence)]),
                Collapsible(
                    summary="Объяснение",
                    blocks=[Paragraph(text=explanation.strip())],
                    open_if_wrong=True,
                ),
            ],
        )

    def _sentence_block(self, number: int, sentence: Task16Sentence) -> Collapsible:
        inner: list[Block] = [
            Quote(lines=[self._esc(sentence.corrected_sentence)]),
            Paragraph(text=sentence.explanation.strip()),
        ]
        return Collapsible(summary=f"Предложение {number}", blocks=inner, open=sentence.wrong)
