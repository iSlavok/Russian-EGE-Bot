"""Форматтер задания 13 (слитно/раздельно НЕ/НИ): exam + drill.

Предложение содержит частицу в формате (НЕ)СЛОВО / (НИ)СЛОВО. В условии показываем как есть,
в разборе раскрываем: слитно → НЕСЛОВО, раздельно → НЕ СЛОВО, подсвечивая <u><b>…</b></u>.
Exam разбор — пер-предложенческие блоки (раскрыт тот, где юзер ошибся). Drill — кнопки Слитно/Раздельно.
Логики выбора/проверки здесь нет — только view-model.
"""
import re
from dataclasses import dataclass

from app.processors.formatters.base_formatter import BaseFormatter
from app.schemas import Block, Collapsible, NumberedList, Paragraph, Quote, ResultView, TaskView

_DISPLAY = {"TOGETHER": "слитно", "SEPARATE": "раздельно"}
_PARTICLE_RE = re.compile(r"\((НЕ|НИ)\)([А-ЯЁ]+)")


@dataclass(frozen=True)
class Task13Sentence:
    """Предложение разбора: шаблон с (НЕ)СЛОВО, ответ (TOGETHER/SEPARATE), объяснение, ошибся ли юзер."""
    sentence: str
    answer: str
    explanation: str
    wrong: bool = False


class Task13Formatter(BaseFormatter):
    TASK_NUMBER = 13

    def condition(self, *, mode: str, answer_type: str, sentences: list[str]) -> TaskView:
        instruction = (
            f"Укажите варианты ответов, в которых **{mode}** пишется **{_DISPLAY[answer_type]}**. "
            "Запишите номера ответов."
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
        sentences: list[Task13Sentence],
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_answer)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=[self._sentence_block(i, sentence) for i, sentence in enumerate(sentences, start=1)],
        )

    def drill_condition(self, *, particle: str, sentence: str) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=f"Укажите, как пишется частица **{self._esc(particle)}** в данном предложении.",
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
        blocks: list[Block] = [Quote(lines=[self._resolve(sentence, answer)])]
        if explanation.strip():
            blocks.append(Paragraph(text=self._esc(explanation.strip())))
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([_DISPLAY[answer]], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(_DISPLAY.get(user_answer, user_answer),
                                                                        strike=True),
            blocks=blocks,
        )

    def _sentence_block(self, number: int, sentence: Task13Sentence) -> Collapsible:
        display = _DISPLAY[sentence.answer]
        inner: list[Block] = [
            Quote(lines=[self._resolve(sentence.sentence, sentence.answer)]),
            Paragraph(text=f"**Пишется {display}.** {self._esc(sentence.explanation.strip())}"),
        ]
        return Collapsible(summary=f"Предложение {number}", blocks=inner, open=sentence.wrong)

    def _resolve(self, sentence: str, answer: str) -> str:
        """Раскрывает (НЕ)СЛОВО → <u><b>НЕСЛОВО</b></u> (слитно) / <u><b>НЕ СЛОВО</b></u> (раздельно)."""
        def repl(match: re.Match[str]) -> str:
            joined = match.group(1) + ("" if answer == "TOGETHER" else " ") + match.group(2)
            return f"<u><b>{joined}</b></u>"
        return _PARTICLE_RE.sub(repl, self._esc(sentence))
