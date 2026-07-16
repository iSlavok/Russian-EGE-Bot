"""Юнит-тесты форматтера заданий 9–12 (чистый, без БД): exam + drill."""
from app.processors.formatters import N9N12Row, N9N12Word, TaskN9N12Formatter
from app.rendering.rich_renderer import RichRenderer

_F9 = TaskN9N12Formatter(9)
_R = RichRenderer()


def _word(template="сл{letter}во", answer="и", *, cb=None, ca=None, expl="Объяснение."):
    return N9N12Word(template=template, answer_letter=answer, context_before=cb, context_after=ca, explanation=expl)


def test_exam_condition_quoted_rows_with_gaps_and_context():
    rows = [N9N12Row(words=[
        _word("произр{letter}стают", expl=""),
        _word("поч{letter}тать", ca="(старших)", expl=""),
    ])]
    out = _R.render_task(_F9.condition(rows))
    assert out.startswith("### Задание 9\n\n")
    assert "\n\n---\n\n" in out
    assert "> 1) произр..стают, поч..тать (старших)" in out


def test_exam_result_correct_rows_collapsed_filled_italic():
    rows = [N9N12Row(words=[_word("сл{letter}во", "и", expl="Корень.")], wrong=False)]
    out = _R.render_result(_F9.result(correct_answer="1", user_answer="1", rows=rows, is_correct=True))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 1")
    assert "<details><summary>Ряд 1</summary>" in out
    assert "_сл<u><b>И</b></u>во_" in out
    assert "Корень." in out


def test_exam_result_wrong_opens_only_wrong_row():
    rows = [
        N9N12Row(words=[_word("а{letter}", "и", expl="e")], wrong=True),
        N9N12Row(words=[_word("б{letter}", "о", expl="e")], wrong=False),
    ]
    out = _R.render_result(_F9.result(correct_answer="2", user_answer="1", rows=rows, is_correct=False))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~1~~\n\n**Правильный ответ:** 2")
    assert "<details open><summary>Ряд 1</summary>" in out
    assert "<details><summary>Ряд 2</summary>" in out


def test_exam_row_words_separated_by_divider():
    rows = [N9N12Row(words=[_word("а{letter}", "и", expl="e1"), _word("б{letter}", "о", expl="e2")])]
    out = _R.render_result(_F9.result(correct_answer="1", user_answer="1", rows=rows, is_correct=True))
    assert "_а<u><b>И</b></u>_" in out
    assert "_б<u><b>О</b></u>_" in out
    assert "---" in out


def test_drill_condition_quote_gap():
    out = _R.render_task(_F9.drill_condition(_word("б{letter}ллетень", "ю", expl="")))
    assert out.startswith("### Задание 9\n\n")
    assert "> б..ллетень" in out


def test_drill_result_correct_underlined_letter_inline_explanation():
    out = _R.render_result(_F9.drill_result(
        word=_word("б{letter}ллетень", "ю", expl="Словарное слово."), user_letter="и", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** б<u>Ю</u>ллетень")
    assert "Словарное слово." in out
    assert "<details" not in out


def test_drill_result_wrong_struck_user_word():
    out = _R.render_result(_F9.drill_result(
        word=_word("б{letter}ллетень", "ю", expl="e"), user_letter="и", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~бИллетень~~\n\n**Правильный ответ:** б<u>Ю</u>ллетень")


def test_heading_uses_instance_task_number():
    out = _R.render_task(TaskN9N12Formatter(11).drill_condition(_word(expl="")))
    assert out.startswith("### Задание 11\n\n")
