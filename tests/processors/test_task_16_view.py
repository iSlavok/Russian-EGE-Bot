"""Юнит-тесты форматтера задания 16 (чистый, без БД): exam + drill."""
from app.processors.tasks.task_16 import Task16Formatter, Task16Sentence
from app.rendering.rich_renderer import RichRenderer

_F = Task16Formatter()
_R = RichRenderer()


def test_exam_condition_quoted_sentences():
    out = _R.render_task(_F.condition(["Предложение один без запятых", "Второе предложение"]))
    assert out.startswith("### Задание 16\n\n")
    assert "поставить **ОДНУ** запятую" in out
    assert "\n\n---\n\n" in out
    assert "> 1) Предложение один без запятых" in out
    assert "> 2) Второе предложение" in out


def test_exam_result_correct_corrected_in_quote():
    sentences = [Task16Sentence(corrected_sentence="Предложение, с запятой.", explanation="ССП.", wrong=False)]
    out = _R.render_result(_F.result(correct_answer="1", user_answer="1", sentences=sentences, is_correct=True))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 1")
    assert "<details><summary>Предложение 1</summary>" in out
    assert "> Предложение, с запятой." in out
    assert "ССП." in out


def test_exam_result_wrong_opens_only_wrong():
    sentences = [
        Task16Sentence(corrected_sentence="c1", explanation="e", wrong=True),
        Task16Sentence(corrected_sentence="c2", explanation="e", wrong=False),
    ]
    out = _R.render_result(_F.result(correct_answer="2", user_answer="1", sentences=sentences, is_correct=False))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~1~~\n\n**Правильный ответ:** 2")
    assert "<details open><summary>Предложение 1</summary>" in out
    assert "<details><summary>Предложение 2</summary>" in out


def test_drill_condition_quote():
    out = _R.render_task(_F.drill_condition("Предложение без запятых"))
    assert out == "### Задание 16\n\nСколько запятых нужно поставить в предложении?\n\n---\n\n> Предложение без запятых"


def test_drill_result_correct_collapsed_explanation():
    out = _R.render_result(_F.drill_result(
        answer="2", user_answer="1", corrected_sentence="Текст, с запятыми, вот.",
        explanation="Правило.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 2")
    assert "> Текст, с запятыми, вот." in out
    assert "<details><summary>Объяснение</summary>" in out
    assert "Правило." in out


def test_drill_result_wrong_opens_explanation():
    out = _R.render_result(_F.drill_result(
        answer="2", user_answer="0", corrected_sentence="c", explanation="e", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~0~~\n\n**Правильный ответ:** 2")
    assert "<details open><summary>Объяснение</summary>" in out
