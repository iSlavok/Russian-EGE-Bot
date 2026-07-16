"""Юнит-тесты форматтера задания 25 (чистый, без БД): только exam."""
from app.processors.tasks.task_25 import Task25Formatter
from app.rendering.rich_renderer import RichRenderer

_F = Task25Formatter()
_R = RichRenderer()


def test_condition_fragment_in_open_details():
    out = _R.render_task(_F.condition(task="Выпишите фразеологизм.", sentences="(31)Текст. (32)Ещё."))
    assert out.startswith("### Задание 25\n\nВыпишите фразеологизм.\n\n---\n\n")
    assert "<details open><summary>Фрагмент текста</summary>" in out
    assert "> (31)Текст. (32)Ещё." in out


def test_result_correct_highlights_user_form_singular_label():
    out = _R.render_result(_F.result(
        forms=["радостный", "радостная"], user_answer="радостная", sentences="Текст.",
        explanation="Форма прилагательного.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** радостный / <u>радостная</u>")
    assert "<details><summary>Объяснение</summary>" in out
    assert "Форма прилагательного." in out
    assert "<details><summary>Фрагмент текста</summary>" in out


def test_result_wrong_singular_label_and_open_explanation():
    out = _R.render_result(_F.result(
        forms=["ответодин", "ответдва"], user_answer="ошибка", sentences="t", explanation="e", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~ошибка~~\n\n**Правильный ответ:** ответодин / ответдва")
    assert "<details open><summary>Объяснение</summary>" in out
