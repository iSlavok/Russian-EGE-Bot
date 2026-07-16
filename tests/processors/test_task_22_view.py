"""Юнит-тесты форматтера задания 22 (чистый, без БД): exam + drill."""
from app.processors.formatters import Task22Formatter, Task22Letter
from app.rendering.rich_renderer import RichRenderer

_F = Task22Formatter()
_R = RichRenderer()


def test_exam_condition_two_open_blocks_and_footer():
    out = _R.render_task(_F.condition(
        sentences=["<b>Метафора тут.</b>", "Эпитет здесь."],
        device_options=["METAPHOR", "EPITHET", "HYPERBOLE"],
    ))
    assert out.startswith("### Задание 22\n\n")
    assert "<details open><summary>Предложения</summary>" in out
    assert "> **А.** <b>Метафора тут.</b>" in out
    assert "> **Б.** Эпитет здесь." in out
    assert "<details open><summary>Средства выразительности</summary>" in out
    assert "1) метафора" in out
    assert "2) эпитет" in out
    assert out.endswith("_Запишите 5 цифр в порядке АБВГД._")


def test_exam_result_correct_letters_collapsed():
    letters = [Task22Letter(number="1", device="METAPHOR", sentence="<b>s1</b>", wrong=False)]
    out = _R.render_result(_F.result(
        correct_answer="1", user_answer="1", letters=letters, device_options=["METAPHOR", "EPITHET"], is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 1")
    assert "<details><summary>А → 1. метафора</summary>" in out
    assert "> <b>s1</b>" in out
    assert "<details><summary>Средства выразительности</summary>" in out


def test_exam_result_wrong_opens_only_wrong_letter():
    letters = [
        Task22Letter(number="1", device="METAPHOR", sentence="s1", wrong=True),
        Task22Letter(number="2", device="EPITHET", sentence="s2", wrong=False),
    ]
    out = _R.render_result(_F.result(
        correct_answer="12", user_answer="3-", letters=letters, device_options=["METAPHOR", "EPITHET"], is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~3-~~\n\n**Правильный ответ:** 12")
    assert "<details open><summary>А → 1. метафора</summary>" in out
    assert "<details><summary>Б → 2. эпитет</summary>" in out


def test_drill_condition_quote():
    out = _R.render_task(_F.drill_condition("<b>Предложение.</b>"))
    assert out == "### Задание 22\n\nОпределите средство выразительности.\n\n---\n\n> <b>Предложение.</b>"


def test_drill_result_correct_highlights_user_device_among_many():
    out = _R.render_result(_F.drill_result(
        devices=["METAPHOR", "EPITHET"], user_device="EPITHET", sentence="s", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** метафора / <u>эпитет</u>")
    assert "> s" in out


def test_drill_result_wrong_struck_user_name():
    out = _R.render_result(_F.drill_result(
        devices=["METAPHOR"], user_device="HYPERBOLE", sentence="s", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~гипербола~~\n\n**Правильный ответ:** метафора")


def test_drill_options_map_values_to_names():
    options = Task22Formatter.drill_options(["METAPHOR", "EPITHET", "HYPERBOLE"])
    assert [option.text for option in options] == ["метафора", "эпитет", "гипербола"]
    assert [option.value for option in options] == ["METAPHOR", "EPITHET", "HYPERBOLE"]
