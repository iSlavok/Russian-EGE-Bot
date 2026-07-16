"""Юнит-тесты форматтера задания 6 (чистый, без БД): exam."""
from app.processors.formatters import Task6Formatter
from app.processors.schemas import Task6Content, Task6Type
from app.rendering.rich_renderer import RichRenderer

_F = Task6Formatter()
_R = RichRenderer()


def _content(task_type: Task6Type = Task6Type.REPLACE) -> Task6Content:
    return Task6Content(
        sentence="Он создал ошибку.",
        task_type=task_type,
        sentence_with_markup="Он <u>сделал</u> ошибку.",
        corrected_sentence="Он <u>создал</u> ошибку.",
    )


def test_condition_replace_instruction_and_quote():
    out = _R.render_task(_F.condition(_content(Task6Type.REPLACE)))
    assert out.startswith("### Задание 6\n\n")
    assert "<b>заменив употреблённое неверно слово.</b>" in out
    assert "\n\n---\n\n" in out
    assert "> Он создал ошибку." in out


def test_condition_remove_instruction():
    out = _R.render_task(_F.condition(_content(Task6Type.REMOVE)))
    assert "<b>исключив лишнее слово.</b>" in out


def test_result_correct_highlights_user_and_builds_sentence_block():
    out = _R.render_result(_F.result(_content(), ["создал"], "создал", "Пояснение.", is_correct=True))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** <u>создал</u>")
    assert "<details><summary>Объяснение</summary>" in out
    assert "Пояснение." in out
    assert "<details><summary>Предложение</summary>" in out
    assert "**Исходное:**" in out
    assert "> Он <s>сделал</s> ошибку." in out
    assert "**Правильное:**" in out
    assert "> Он <u><b>создал</b></u> ошибку." in out


def test_result_wrong_struck_and_open_explanation():
    out = _R.render_result(_F.result(_content(), ["создал"], "сделал", "Пояснение.", is_correct=False))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~сделал~~\n\n**Правильный ответ:** создал")
    assert "<details open><summary>Объяснение</summary>" in out


def test_result_multiple_answers_label_and_highlight():
    out = _R.render_result(_F.result(_content(), ["создал", "сделал"], "сделал", "e", is_correct=True))
    assert "**Ответы:** создал / <u>сделал</u>" in out
