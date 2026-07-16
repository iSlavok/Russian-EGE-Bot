"""Юнит-тесты форматтера задания 26 (чистый, без БД): только exam."""
from app.processors.formatters import Task26Formatter
from app.rendering.rich_renderer import RichRenderer

_F = Task26Formatter()
_R = RichRenderer()


def test_condition_fragment_in_open_details():
    out = _R.render_task(_F.condition(task="Среди предложений найдите...", sentences="(1)Текст. (2)Ещё."))
    assert out.startswith("### Задание 26\n\nСреди предложений найдите...\n\n---\n\n")
    assert "<details open><summary>Фрагмент текста</summary>" in out
    assert "> (1)Текст. (2)Ещё." in out


def test_result_correct_three_blocks():
    out = _R.render_result(_F.result(
        correct_answer="9", user_answer="9", sentences="Текст.", explanation="Лексический повтор.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 9")
    assert "<details><summary>Объяснение</summary>" in out
    assert "Лексический повтор." in out
    assert "<details><summary>Фрагмент текста</summary>" in out


def test_result_wrong_dash_and_open_explanation():
    out = _R.render_result(_F.result(
        correct_answer="9", user_answer="", sentences="t", explanation="e", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~—~~\n\n**Правильный ответ:** 9")
    assert "<details open><summary>Объяснение</summary>" in out
