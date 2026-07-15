"""Базовый форматтер: общие билдеры Rich-вёрстки для заданий.

Пер-таск форматтеры наследуют его (как процессоры наследуют `BaseTaskProcessor`).
Форматтеры получают сырые доменные данные и собирают view-model (`TaskView`/`ResultView`);
рендер view → Rich MD делает `app.rendering.rich_renderer.RichRenderer`.
"""
import html

from app.schemas import AnswerLine, Collapsible, Quote


class BaseFormatter:
    GAP = "< . . . >"

    @staticmethod
    def _esc(text: str) -> str:
        return html.escape(text, quote=False)

    def _text_quote(self, text: str) -> Quote:
        """Текст в цитате (многострочный — построчно), с экранированием."""
        return Quote(lines=self._esc(text).split("\n"))

    def _fill_gap(self, text: str, word: str) -> str:
        """Вставить `word` в пропуск, подсветив `<u><b>…</b></u>`; остальное экранировать."""
        return f"<u><b>{self._esc(word)}</b></u>".join(self._esc(part) for part in text.split(self.GAP))

    @staticmethod
    def _answer_line(values: list[str], user_answer: str, *, is_correct: bool) -> AnswerLine:
        """Строка ответа: «Ответ/Ответы» (верно, ответ юзера подчёркнут) или «Правильный ответ(ы)»."""
        if is_correct:
            return AnswerLine(label="Ответ" if len(values) == 1 else "Ответы", values=values, user=user_answer)
        return AnswerLine(label="Правильный ответ" if len(values) == 1 else "Правильные ответы", values=values)

    @staticmethod
    def _your_answer_line(user_answer: str) -> AnswerLine:
        """Строка «Ваш ответ» (зачёркивается рендерером как неверная)."""
        return AnswerLine(label="Ваш ответ", values=[user_answer])

    def _gap_fragment(self, text: str, word: str, *, summary: str = "Фрагмент текста") -> Collapsible:
        """Свёрнутый блок с фрагментом текста, где в пропуск вставлен подсвеченный ответ."""
        return Collapsible(summary=summary, blocks=[Quote(lines=[self._fill_gap(text, word)])], open_if_wrong=True)
