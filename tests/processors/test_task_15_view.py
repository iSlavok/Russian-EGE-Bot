"""Юнит-тесты форматтера задания 15 (чистый, без БД): exam + drill."""
from app.processors.tasks.task_15 import Task15Formatter
from app.rendering.rich_renderer import RichRenderer

_F = Task15Formatter()
_R = RichRenderer()


def test_exam_condition_formulation_n():
    out = _R.render_task(_F.condition(mode="Н", sentence="Серебря(1)ый кова(2)ый."))
    assert out.startswith("### Задание 15\n\n")
    assert "пишется **одна буква Н**." in out
    assert "\n\n---\n\n" in out
    assert "> Серебря(1)ый кова(2)ый." in out


def test_exam_condition_formulation_nn():
    out = _R.render_task(_F.condition(mode="НН", sentence="x"))
    assert "пишется **НН**." in out


def test_exam_result_correct_corrected_in_quote():
    out = _R.render_result(_F.result(
        correct_answer="12", user_answer="12", corrected_sentence="Серебряный кованый.",
        explanation="Правило.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 12")
    assert "> Серебряный кованый." in out
    assert "<details><summary>Объяснение</summary>" in out
    assert "Правило." in out


def test_exam_result_wrong_opens_explanation():
    out = _R.render_result(_F.result(
        correct_answer="12", user_answer="1", corrected_sentence="c", explanation="e", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~1~~\n\n**Правильный ответ:** 12")
    assert "<details open><summary>Объяснение</summary>" in out


def test_drill_condition_bold_gap_in_quote():
    out = _R.render_task(_F.drill_condition(sentence="Дом стекля{n}ый."))
    assert out == "### Задание 15\n\nВставьте пропущенные буквы.\n\n---\n\n> Дом стекля**(н/нн)**ый."


def test_drill_result_correct_underlined_letter_in_word():
    out = _R.render_result(_F.drill_result(
        word="стекля{n}ый", sentence="Дом стекля{n}ый.", answer="нн", user_answer="н",
        explanation="Отымённое.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** стекля<u>НН</u>ый")
    assert "> Дом стекля<u>нн</u>ый." in out
    assert "Отымённое." in out
    assert "<details" not in out


def test_drill_result_wrong_shows_user_word_struck():
    out = _R.render_result(_F.drill_result(
        word="стекля{n}ый", sentence="Дом стекля{n}ый.", answer="нн", user_answer="н",
        explanation="e", is_correct=False,
    ))
    assert out.startswith(
        "**❌ Неверно**\n\n**Ваш ответ:** ~~стекля<u>Н</u>ый~~\n\n**Правильный ответ:** стекля<u>НН</u>ый",
    )
