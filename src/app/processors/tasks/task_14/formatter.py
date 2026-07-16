"""Форматтер задания 14 (слитно/раздельно/дефис): exam + drill.

Exam: 5 предложений (2 слова в скобках), в разборе — готовое `corrected_sentence` в цитате.
Drill: 1 слово в скобках, 3 кнопки; в разборе скобка раскрывается regex'ом с подсветкой <u><b>…</b></u>.
Exam разбор — пер-предложенческие блоки (раскрыт тот, где юзер ошибся).
Логики выбора/проверки здесь нет — только view-model.
"""
import re
from dataclasses import dataclass

from app.processors._base.base_formatter import BaseFormatter
from app.schemas import Block, Collapsible, NumberedList, Paragraph, Quote, ResultView, TaskView

_HARD_BREAK = "  \n"  # внутри <details> одиночный \n схлопывается
_DISPLAY = {"TOGETHER": "слитно", "SEPARATE": "раздельно", "HYPHEN": "через дефис"}
_JOIN = {"TOGETHER": "", "SEPARATE": " ", "HYPHEN": "-"}
_BRACKET_PREFIX_RE = re.compile(r"\(([А-ЯЁ]+)\)([А-ЯЁ]+)")
_BRACKET_SUFFIX_RE = re.compile(r"([А-ЯЁ]+)\(([А-ЯЁ]+)\)")


@dataclass(frozen=True)
class Task14Sentence:
    """Предложение разбора exam: готовое раскрытое предложение, объяснение, ошибся ли юзер."""
    corrected_sentence: str
    explanation: str
    wrong: bool = False


class Task14Formatter(BaseFormatter):
    TASK_NUMBER = 14

    def condition(self, *, answer_type: str, sentences: list[str]) -> TaskView:
        instruction = (
            f"Укажите варианты ответов, в которых оба выделенных слова пишутся "
            f"**{_DISPLAY[answer_type].upper()}**. Запишите номера ответов."
        )
        return TaskView(
            heading=self.heading,
            instruction=instruction,
            blocks=[NumberedList(items=[self._esc(sentence) for sentence in sentences], quoted=True, paren=True)],
        )

    def result(
        self,
        *,
        correct_answer: str,
        user_answer: str,
        sentences: list[Task14Sentence],
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
            instruction="Определите написание слова в скобках.",
            blocks=[self._text_quote(sentence)],
        )

    def drill_result(
        self,
        *,
        sentence: str,
        answer: str,
        user_answer: str,
        explanation: str,
        is_correct: bool,
    ) -> ResultView:
        blocks: list[Block] = [Quote(lines=[self._resolve_one(sentence, answer)])]
        if explanation.strip():
            blocks.append(Paragraph(text=explanation.strip()))
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([_DISPLAY[answer]], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(_DISPLAY.get(user_answer, user_answer),
                                                                        strike=True),
            blocks=blocks,
        )

    def _sentence_block(self, number: int, sentence: Task14Sentence) -> Collapsible:
        inner: list[Block] = [
            Quote(lines=[self._esc(sentence.corrected_sentence)]),
            Paragraph(text=sentence.explanation.strip().replace("\n", _HARD_BREAK)),
        ]
        return Collapsible(summary=f"Предложение {number}", blocks=inner, open=sentence.wrong)

    def _resolve_one(self, sentence: str, answer: str) -> str:
        """Раскрывает скобку (в любой позиции) по типу написания, подсвечивая <u><b>…</b></u>."""
        join = _JOIN[answer]

        def repl(match: re.Match[str]) -> str:
            return f"<u><b>{match.group(1)}{join}{match.group(2)}</b></u>"

        resolved = _BRACKET_PREFIX_RE.sub(repl, self._esc(sentence))
        return _BRACKET_SUFFIX_RE.sub(repl, resolved)
