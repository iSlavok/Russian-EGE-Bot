"""Форматтер задания 8 (синтакс. нормы: соответствие А–Д ↔ предложения): exam + drill.

Exam условие: два <details open> — «Грамматические ошибки» (А–Д) и «Предложения» (1–9) + футер.
Exam разбор: верх + пер-буквенные блоки А–Д (раскрыт тот, где юзер ошибся) + свёрнутый «Предложения».
Drill: 1 предложение + 10 кнопок-типов; разбор — вердикт + свёрнутый «Объяснение» (открыт при неверном).
Логики выбора/проверки здесь нет — только view-model. Дисплей-подписи типов ошибок живут здесь.
"""
from dataclasses import dataclass

from app.processors._base.base_formatter import BaseFormatter
from app.schemas import Block, Collapsible, NumberedList, Paragraph, Quote, ResultView, TaskOption, TaskView

_LETTERS = ["А", "Б", "В", "Г", "Д"]

_DESCRIPTIONS = {
    "participial_clause_error": "нарушение в построении предложения с причастным оборотом",
    "homogeneous_members_error": "ошибка в построении предложения с однородными членами",
    "adverbial_participle_error": "неправильное построение предложения с деепричастным оборотом",
    "prepositional_case_error": "неправильное употребление падежной формы существительного с предлогом",
    "subject_predicate_agreement": "нарушение связи между подлежащим и сказуемым",
    "mismatched_appositive_error": "нарушение в построении предложения с несогласованным приложением",
    "complex_sentence_error": "ошибка в построении сложного предложения",
    "indirect_speech_error": "неправильное построение предложения с косвенной речью",
    "verb_aspect_tense_error": "нарушение видо-временной соотнесённости глагольных форм",
    "numeral_usage_error": "неправильное употребление имени числительного",
}

_SHORT_LABELS = {
    "subject_predicate_agreement": "Подлежащее и сказуемое",
    "adverbial_participle_error": "Деепричастный оборот",
    "participial_clause_error": "Причастный оборот",
    "homogeneous_members_error": "Однородные члены",
    "prepositional_case_error": "Падежная форма",
    "verb_aspect_tense_error": "Видо-время глаголов",
    "mismatched_appositive_error": "Несоглас. приложение",
    "complex_sentence_error": "Сложное предложение",
    "indirect_speech_error": "Косвенная речь",
    "numeral_usage_error": "Числительное",
}


@dataclass(frozen=True)
class Task8Letter:
    """Данные одной буквы А–Д для разбора: тип ошибки, номер предложения, тексты, ошибся ли юзер."""
    error_type: str
    position: int
    explanation: str
    sentence: str
    corrected_sentence: str | None
    wrong: bool


class Task8Formatter(BaseFormatter):
    TASK_NUMBER = 8
    EXAM_INSTRUCTION = (
        "Установите соответствие между грамматическими ошибками и предложениями, в которых они допущены: "
        "к каждой позиции первого столбца подберите соответствующую позицию из второго столбца."
    )
    DRILL_INSTRUCTION = "Определите тип грамматической ошибки в предложении."
    FOOTER = "Запишите цифры для АБВГД."

    def condition(self, error_type_order: list[str], sentences: list[str]) -> TaskView:
        error_lines = [f"{_LETTERS[i]}) {self._esc(_DESCRIPTIONS.get(error_type, error_type))}"
                       for i, error_type in enumerate(error_type_order)]
        return TaskView(
            heading=self.heading,
            instruction=self.EXAM_INSTRUCTION,
            blocks=[
                Collapsible(summary="Грамматические ошибки", blocks=[Quote(lines=error_lines)], open=True),
                Collapsible(summary="Предложения", blocks=[self._sentences_list(sentences)], open=True),
            ],
            footer=self.FOOTER,
        )

    def result(
        self,
        *,
        correct_answer: str,
        user_answer: str,
        letters: list[Task8Letter],
        sentences: list[str],
        is_correct: bool,
    ) -> ResultView:
        letter_blocks: list[Block] = [self._letter_block(_LETTERS[i], letter) for i, letter in enumerate(letters)]
        letter_blocks.append(Collapsible(summary="Предложения", blocks=[self._sentences_list(sentences)]))
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_answer)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=letter_blocks,
        )

    def drill_condition(self, sentence: str) -> TaskView:
        return TaskView(
            heading=self.heading,
            instruction=f"**{self.DRILL_INSTRUCTION}**",
            blocks=[self._text_quote(sentence)],
        )

    def drill_result(
        self,
        *,
        correct_type: str,
        user_type: str,
        explanation: str,
        sentence: str,
        corrected_sentence: str | None,
        is_correct: bool,
    ) -> ResultView:
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(_SHORT_LABELS.get(correct_type, correct_type))], "",
                                     is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(
                self._esc(_SHORT_LABELS.get(user_type, user_type)), strike=True),
            blocks=[
                Collapsible(
                    summary="Объяснение",
                    blocks=self._sentence_inner(explanation, sentence, corrected_sentence),
                    open_if_wrong=True,
                ),
            ],
        )

    @staticmethod
    def drill_options() -> list[TaskOption]:
        return [TaskOption(text=label, value=error_type) for error_type, label in _SHORT_LABELS.items()]

    def _sentences_list(self, sentences: list[str]) -> NumberedList:
        return NumberedList(items=[self._esc(sentence) for sentence in sentences], paren=True)

    def _letter_block(self, label: str, letter: Task8Letter) -> Collapsible:
        summary = f"{label} → {letter.position}. {self._esc(_SHORT_LABELS.get(letter.error_type, letter.error_type))}"
        return Collapsible(
            summary=summary,
            blocks=self._sentence_inner(letter.explanation, letter.sentence, letter.corrected_sentence),
            open=letter.wrong,
        )

    def _sentence_inner(self, explanation: str, sentence: str, corrected_sentence: str | None) -> list[Block]:
        """Внутренность блока: объяснение (без заголовка) → Исходное предложение → Правильное предложение."""
        blocks: list[Block] = [
            Paragraph(text=explanation.replace("\n", "\n\n")),
            Paragraph(text="**Исходное предложение:**"),
            Quote(lines=[self._esc(sentence)]),
        ]
        if corrected_sentence:
            blocks.append(Paragraph(text="**Правильное предложение:**"))
            blocks.append(Quote(lines=[corrected_sentence]))
        return blocks
