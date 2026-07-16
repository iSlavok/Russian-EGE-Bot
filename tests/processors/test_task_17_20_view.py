"""Юнит-тесты форматтера заданий 17–20 (чистый, без БД): только exam."""
from app.processors.tasks.task_17_20 import TaskN17N20Formatter
from app.rendering.rich_renderer import RichRenderer

_F = TaskN17N20Formatter(17)
_R = RichRenderer()


def test_condition_formulation_and_quote():
    out = _R.render_task(_F.condition("Пришёл (1) увидел (2) победил."))
    assert out.startswith("### Задание 17\n\n")
    assert "Расставьте все знаки препинания" in out
    assert "\n\n---\n\n" in out
    assert "> Пришёл (1) увидел (2) победил." in out


def test_result_correct_corrected_in_quote():
    out = _R.render_result(_F.result(
        correct_answer="12", user_answer="12", correct_sentence="Пришёл, увидел, победил.",
        explanation="Однородные члены.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 12")
    assert "> Пришёл, увидел, победил." in out
    assert "<details><summary>Объяснение</summary>" in out
    assert "Однородные члены." in out


def test_result_wrong_opens_and_dash_for_empty_answer():
    out = _R.render_result(_F.result(
        correct_answer="12", user_answer="", correct_sentence="c", explanation="e", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~—~~\n\n**Правильный ответ:** 12")
    assert "<details open><summary>Объяснение</summary>" in out


def test_heading_uses_instance_task_number():
    out = _R.render_task(TaskN17N20Formatter(20).condition("x"))
    assert out.startswith("### Задание 20\n\n")
