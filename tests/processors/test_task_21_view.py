"""Юнит-тесты форматтера задания 21 (чистый, без БД): exam + drill."""
from app.processors.tasks.task_21 import Task21Formatter
from app.processors.tasks.task_21 import Task21TaskType
from app.rendering.rich_renderer import RichRenderer

_F = Task21Formatter()
_R = RichRenderer()


def test_exam_condition_text_in_open_details():
    out = _R.render_task(_F.condition(task_type=Task21TaskType.COMMA, full_text="(1)Текст (2)ещё."))
    assert out.startswith("### Задание 21\n\n")
    assert "Найдите предложения, в которых запятая" in out
    assert "\n\n---\n\n" in out
    assert "<details open><summary>Текст</summary>" in out
    assert "> (1)Текст (2)ещё." in out


def test_exam_result_correct_answer_with_rule():
    out = _R.render_result(_F.result(
        task_type=Task21TaskType.COMMA, answer="13", answer_rule="HOMOGENEOUS", user_answer="13",
        full_text="текст", explanation="Правило.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 13 — Однородные члены")
    assert "<details><summary>Объяснение</summary>" in out
    assert "Правило." in out
    assert "<details><summary>Текст</summary>" in out


def test_exam_result_wrong_dash_and_open_explanation():
    out = _R.render_result(_F.result(
        task_type=Task21TaskType.COMMA, answer="13", answer_rule="HOMOGENEOUS", user_answer="",
        full_text="t", explanation="e", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~—~~\n\n**Правильный ответ:** 13 — Однородные члены")
    assert "<details open><summary>Объяснение</summary>" in out


def test_drill_condition_and_options():
    out = _R.render_task(_F.drill_condition(task_type=Task21TaskType.COLON, text="Он сказал: пора."))
    assert out.startswith(
        "### Задание 21\n\nПо какому правилу в этом предложении ставится двоеточие?\n\n---\n\n> Он сказал: пора.",
    )
    options = Task21Formatter.drill_options(Task21TaskType.COLON)
    assert len(options) == 3
    assert all(option.text and option.value for option in options)


def test_drill_result_correct_uses_rule_name():
    out = _R.render_result(_F.drill_result(
        task_type=Task21TaskType.COMMA, answer="HOMOGENEOUS", user_answer="SSP",
        text="Текст.", explanation="Правило.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** Однородные члены")
    assert "> Текст." in out
    assert "<details><summary>Объяснение</summary>" in out


def test_drill_result_wrong_maps_both_rule_names():
    out = _R.render_result(_F.drill_result(
        task_type=Task21TaskType.COMMA, answer="HOMOGENEOUS", user_answer="SSP",
        text="t", explanation="e", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~ССП~~\n\n**Правильный ответ:** Однородные члены")
    assert "<details open><summary>Объяснение</summary>" in out
