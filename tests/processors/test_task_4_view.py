"""Юнит-тесты форматтера задания 4 (чистый, без БД): exam + drill."""
from app.processors.tasks.task_04 import Task4Formatter
from app.processors.tasks.task_04 import Task4Content
from app.rendering.rich_renderer import RichRenderer

_F = Task4Formatter()
_R = RichRenderer()


def test_exam_condition_numbered_quoted_uppercase_stress():
    contents = [Task4Content(word="банты", incorrect_stress=5), Task4Content(word="дефис", incorrect_stress=1)]
    out = _R.render_task(_F.condition(contents, [2, 4]))
    assert out.startswith("### Задание 4\n\n")
    assert "\n\n---\n\n" in out
    assert "> 1) бАнты" in out
    assert "> 2) дефИс" in out


def test_exam_result_correct_collapses_explanation():
    out = _R.render_result(_F.result(["<b>бАнты</b> — правило", "<b>дефИс</b> — правило"], "12", "12", is_correct=True))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 12")
    assert "<details><summary>Объяснение</summary>" in out
    assert "1) <b>бАнты</b> — правило" in out
    assert "Варианты ответов" not in out


def test_exam_result_wrong_opens_and_not_struck():
    out = _R.render_result(_F.result(["e1", "e2"], "12", "13", is_correct=False))
    # как в config.py: «Ваш ответ» НЕ зачёркивается
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** 13\n\n**Правильный ответ:** 12")
    assert "<details open><summary>Объяснение</summary>" in out


def test_drill_condition_no_divider():
    out = _R.render_task(_F.drill_condition(Task4Content(word="банты", incorrect_stress=2)))
    assert out == "### Задание 4\n\nВыберите правильное ударение в слове: **банты**."


def test_drill_condition_keeps_context():
    content = Task4Content(word="банты", incorrect_stress=2, context_before="красивые", context_after="на столе")
    out = _R.render_task(_F.drill_condition(content))
    assert out == "### Задание 4\n\nВыберите правильное ударение в слове: **красивые банты на столе**."


def test_drill_result_inline_explanation():
    out = _R.render_result(_F.drill_result("<b>бАнты</b> — правило", is_correct=True))
    assert out == "**✅ Верно**\n\n<b>бАнты</b> — правило"
