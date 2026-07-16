"""Юнит-тесты форматтера задания 7 (чистый, без БД): exam + drill."""
from app.processors.tasks.task_07 import Task7Formatter
from app.rendering.rich_renderer import RichRenderer

_F = Task7Formatter()
_R = RichRenderer()


def test_exam_condition_quoted_numbered_bold_uppercase():
    shown = [("не менее {word} участников", "восьмисот"), ("пара {word}", "туфель")]
    out = _R.render_task(_F.condition(shown))
    assert out.startswith("### Задание 7\n\n")
    assert "\n\n---\n\n" in out
    assert "> 1) не менее <b>ВОСЬМИСОТ</b> участников" in out
    assert "> 2) пара <b>ТУФЕЛЬ</b>" in out


def test_exam_result_correct_divider_quote_and_collapsibles():
    out = _R.render_result(_F.result(
        correct_word="их",
        phrase_template="{word} книги",
        explanation="Пояснение.",
        shown=[("{word} книги", "ихние")],
        user_answer="их",
        is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** их\n\n---\n\n> <u><b>Их</b></u> книги")
    assert "<details><summary>Объяснение</summary>" in out
    assert "Пояснение." in out
    assert "<details><summary>Словосочетания</summary>" in out


def test_exam_result_wrong_struck_and_open_explanation():
    out = _R.render_result(_F.result(
        correct_word="их",
        phrase_template="{word} книги",
        explanation="e",
        shown=[("{word} книги", "ихние")],
        user_answer="ихние",
        is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~ихние~~\n\n**Правильный ответ:** их\n\n---\n\n")
    assert "<details open><summary>Объяснение</summary>" in out


def test_drill_condition_no_divider():
    out = _R.render_task(_F.drill_condition())
    assert out == "### Задание 7\n\nВыберите словосочетание, в котором нет грамматической ошибки."


def test_drill_result_inline_explanation_no_collapsible():
    out = _R.render_result(_F.drill_result(
        correct_word="туфель",
        phrase_template="пара {word}",
        explanation="Правильно: туфель.",
        user_answer="туфлей",
        is_correct=False,
    ))
    assert out.startswith(
        "**❌ Неверно**\n\n**Ваш ответ:** ~~туфлей~~\n\n**Правильный ответ:** туфель\n\n---\n\n> пара <u><b>туфель</b></u>",
    )
    assert "Правильно: туфель." in out
    assert "<details" not in out  # объяснение инлайн, без свёрнутого блока
