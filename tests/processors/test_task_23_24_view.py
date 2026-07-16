"""Юнит-тесты форматтера заданий 23–24 (чистый, без БД): только exam."""
from app.processors.tasks.task_23_24 import Task2324Formatter
from app.rendering.rich_renderer import RichRenderer

_F23 = Task2324Formatter(23)
_F24 = Task2324Formatter(24)
_R = RichRenderer()


def test_condition_23_correct_mode():
    out = _R.render_task(_F23.condition(ask_incorrect=False, text="Текст статьи.", options=["Утв1", "Утв2"]))
    assert out.startswith("### Задание 23\n\n")
    assert "соответствуют содержанию текста" in out
    assert "не соответствуют" not in out
    assert "\n\n---\n\n" in out
    assert "<details open><summary>Текст</summary>" in out
    assert "> Текст статьи." in out
    assert "**Высказывания:**" in out
    assert "1. Утв1" in out


def test_condition_23_incorrect_mode_uses_bold_negation():
    out = _R.render_task(_F23.condition(ask_incorrect=True, text="t", options=["a"]))
    assert "<b>не соответствуют</b>" in out


def test_condition_24_uses_utverzhdeniya_label():
    out = _R.render_task(_F24.condition(ask_incorrect=False, text="t", options=["a"]))
    assert out.startswith("### Задание 24\n\n")
    assert "являются верными" in out
    assert "**Утверждения:**" in out


def test_result_23_correct_three_collapsed_blocks():
    out = _R.render_result(_F23.result(
        correct_answer="13", user_answer="13", text="Текст.", options=["Утв1", "Утв2"],
        explanation="Разбор.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 13")
    assert "<details><summary>Объяснение</summary>" in out
    assert "Разбор." in out
    assert "<details><summary>Высказывания</summary>" in out
    assert "<details><summary>Текст</summary>" in out


def test_result_24_wrong_opens_explanation():
    out = _R.render_result(_F24.result(
        correct_answer="13", user_answer="—", text="t", options=["a"], explanation="e", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~—~~\n\n**Правильный ответ:** 13")
    assert "<details open><summary>Объяснение</summary>" in out
    assert "<details><summary>Утверждения</summary>" in out
