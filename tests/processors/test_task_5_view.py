"""Юнит-тесты форматтера задания 5 (чистый, без БД): exam + drill."""
from app.processors.tasks.task_05 import Task5Formatter
from app.rendering.rich_renderer import RichRenderer

_F = Task5Formatter()
_R = RichRenderer()

_TPL = "Он был {word} человеком."


def test_exam_condition_quoted_numbered_bold_uppercase():
    shown = [(_TPL, "дипломатичным"), ("Это {word} вопрос.", "принципиальный")]
    out = _R.render_task(_F.condition(shown))
    assert out.startswith("### Задание 5\n\n")
    assert "<b>НЕВЕРНО</b>" in out  # HTML инструкции сохраняется
    assert "\n\n---\n\n" in out
    assert "> 1) Он был <b>ДИПЛОМАТИЧНЫМ</b> человеком." in out
    assert "> 2) Это <b>ПРИНЦИПИАЛЬНЫЙ</b> вопрос." in out


def test_exam_result_correct_full_structure():
    out = _R.render_result(_F.result(
        correct_word="дипломатичным",
        wrong_word="дипломатическим",
        sentence_template=_TPL,
        paronym_explanations=["Тактичный", "Относящийся к дипломатии"],
        shown=[(_TPL, "дипломатическим")],
        user_answer="дипломатичным",
        is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** дипломатичным")
    assert "**Неправильное слово в задании:** дипломатическим" in out
    assert "> Он был <u>дипломатичным</u> человеком." in out
    assert "<details><summary>Объяснение</summary>" in out
    assert "Тактичный" in out
    assert "<details><summary>Предложения</summary>" in out


def test_exam_result_wrong_struck_and_open_explanation():
    out = _R.render_result(_F.result(
        correct_word="дипломатичным",
        wrong_word="дипломатическим",
        sentence_template=_TPL,
        paronym_explanations=["a", "b"],
        shown=[(_TPL, "дипломатическим")],
        user_answer="ошибка",
        is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~ошибка~~\n\n**Правильный ответ:** дипломатичным")
    assert "<details open><summary>Объяснение</summary>" in out


def test_corrected_sentence_capitalized_when_word_at_start():
    out = _R.render_result(_F.drill_result(
        correct_word="дипломатичный",
        sentence_template="{word} человек пришёл.",
        paronym_explanations=["x"],
        user_answer="",
        is_correct=True,
    ))
    assert "> <u>Дипломатичный</u> человек пришёл." in out


def test_drill_condition_gap_in_quote():
    out = _R.render_task(_F.drill_condition(_TPL))
    assert out.startswith("### Задание 5\n\n")
    assert "\n\n---\n\n" in out
    assert "> Он был &lt; . . . &gt; человеком." in out


def test_drill_result_wrong_struck():
    out = _R.render_result(_F.drill_result(
        correct_word="дипломатичным",
        sentence_template=_TPL,
        paronym_explanations=["x", "y"],
        user_answer="плохо",
        is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~плохо~~\n\n**Правильный ответ:** дипломатичным")
    assert "> Он был <u>дипломатичным</u> человеком." in out
    assert "<details open><summary>Объяснение</summary>" in out
