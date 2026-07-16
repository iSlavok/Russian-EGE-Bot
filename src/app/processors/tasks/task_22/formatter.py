"""Форматтер задания 22 (средства выразительности: соответствие А–Д ↔ 9 приёмов): exam + drill.

Exam условие: два <details open> — «Предложения» (А–Д) и «Средства выразительности» (1–9) + футер.
Exam разбор: верх + пер-буквенные блоки А–Д (раскрыт тот, где юзер ошибся) + свёрнутый список средств.
Drill: 1 предложение + 5 кнопок-средств; разбор — средство(а) (ответ юзера подчёркнут) + предложение.
Предложения содержат HTML (<b>, <u>) — отдаём как есть. Дисплей-подписи средств — DEVICE_NAMES.
Логики выбора/проверки здесь нет — только view-model.
"""
from dataclasses import dataclass

from app.processors._base.base_formatter import BaseFormatter
from app.schemas import Block, Collapsible, NumberedList, Quote, ResultView, TaskOption, TaskView

from .schemas import DEVICE_NAMES

_LETTERS = ["А", "Б", "В", "Г", "Д"]


@dataclass(frozen=True)
class Task22Letter:
    """Данные буквы А–Д для разбора: показанная цифра, верное средство, предложение, ошибся ли юзер."""
    number: str
    device: str
    sentence: str
    wrong: bool


class Task22Formatter(BaseFormatter):
    TASK_NUMBER = 22
    EXAM_FORMULATION = (
        "Прочитайте фрагменты текстов и определите, какое средство выразительности "
        "использовано в каждом предложении. Запишите цифры в порядке, соответствующем буквам."
    )
    DRILL_FORMULATION = "Определите средство выразительности."
    FOOTER = "Запишите 5 цифр в порядке АБВГД."

    def condition(self, *, sentences: list[str], device_options: list[str]) -> TaskView:
        sentence_lines = [f"**{_LETTERS[i]}.** {sentence}" for i, sentence in enumerate(sentences)]
        return TaskView(
            heading=self.heading,
            instruction=self.EXAM_FORMULATION,
            blocks=[
                Collapsible(summary="Предложения", blocks=[Quote(lines=sentence_lines)], open=True),
                Collapsible(summary="Средства выразительности", blocks=[self._devices_list(device_options)], open=True),
            ],
            footer=self.FOOTER,
        )

    def result(
        self,
        *,
        correct_answer: str,
        user_answer: str,
        letters: list[Task22Letter],
        device_options: list[str],
        is_correct: bool,
    ) -> ResultView:
        blocks: list[Block] = [self._letter_block(_LETTERS[i], letter) for i, letter in enumerate(letters)]
        blocks.append(Collapsible(summary="Средства выразительности", blocks=[self._devices_list(device_options)]))
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._esc(correct_answer)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(self._esc(user_answer), strike=True),
            blocks=blocks,
        )

    def drill_condition(self, sentence: str) -> TaskView:
        return TaskView(heading=self.heading, instruction=self.DRILL_FORMULATION, blocks=[Quote(lines=[sentence])])

    def drill_result(
        self,
        *,
        devices: list[str],
        user_device: str,
        sentence: str,
        is_correct: bool,
    ) -> ResultView:
        highlight = user_device if is_correct else None
        return ResultView(
            correct=is_correct,
            answer=self._answer_line([self._dev_line(devices, highlight)], "", is_correct=is_correct),
            wrong_answer=None if is_correct else self._your_answer_line(
                DEVICE_NAMES.get(user_device, user_device), strike=True),
            blocks=[Quote(lines=[sentence])],
        )

    @staticmethod
    def drill_options(device_values: list[str]) -> list[TaskOption]:
        return [TaskOption(text=DEVICE_NAMES[value], value=value) for value in device_values]

    @staticmethod
    def _devices_list(device_options: list[str]) -> NumberedList:
        return NumberedList(items=[DEVICE_NAMES[device] for device in device_options], paren=True)

    @staticmethod
    def _letter_block(label: str, letter: Task22Letter) -> Collapsible:
        summary = f"{label} → {letter.number}. {DEVICE_NAMES.get(letter.device, letter.device)}"
        return Collapsible(summary=summary, blocks=[Quote(lines=[letter.sentence])], open=letter.wrong)

    @staticmethod
    def _dev_line(devices: list[str], highlight: str | None) -> str:
        return " / ".join(
            f"<u>{DEVICE_NAMES[device]}</u>" if device == highlight else DEVICE_NAMES[device]
            for device in devices
        )
