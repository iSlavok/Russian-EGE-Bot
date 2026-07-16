"""Юнит-тесты форматтера задания 13 (чистый, без БД): exam + drill."""
from app.processors.tasks.task_13 import Task13Formatter, Task13Sentence
from app.rendering.rich_renderer import RichRenderer

_F = Task13Formatter()
_R = RichRenderer()


def test_exam_condition_instruction_and_quoted_sentences():
    out = _R.render_task(_F.condition(
        mode="НЕ", answer_type="TOGETHER", sentences=["Это (НЕ)ПРАВДА.", "Совсем (НЕ)ПРОСТО."],
    ))
    assert out.startswith("### Задание 13\n\n")
    assert "в которых **НЕ** пишется **слитно**" in out
    assert "\n\n---\n\n" in out
    assert "> 1) Это (НЕ)ПРАВДА." in out
    assert "> 2) Совсем (НЕ)ПРОСТО." in out


def test_exam_result_correct_resolves_together():
    sentences = [Task13Sentence(sentence="Это (НЕ)ПРАВДА.", answer="TOGETHER", explanation="Синоним ложь.", wrong=False)]
    out = _R.render_result(_F.result(correct_answer="1", user_answer="1", sentences=sentences, is_correct=True))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 1")
    assert "<details><summary>Предложение 1</summary>" in out
    assert "> Это <u><b>НЕПРАВДА</b></u>." in out
    assert "**Пишется слитно.** Синоним ложь." in out


def test_exam_result_wrong_resolves_separate_and_opens_wrong():
    sentences = [
        Task13Sentence(sentence="Вовсе (НЕ)ПРОСТО.", answer="SEPARATE", explanation="e", wrong=True),
        Task13Sentence(sentence="Это (НЕ)ПРАВДА.", answer="TOGETHER", explanation="e", wrong=False),
    ]
    out = _R.render_result(_F.result(correct_answer="2", user_answer="1", sentences=sentences, is_correct=False))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~1~~\n\n**Правильный ответ:** 2")
    assert "<details open><summary>Предложение 1</summary>" in out
    assert "> Вовсе <u><b>НЕ ПРОСТО</b></u>." in out
    assert "**Пишется раздельно.**" in out
    assert "<details><summary>Предложение 2</summary>" in out


def test_drill_condition_bold_particle_and_quote():
    out = _R.render_task(_F.drill_condition(particle="НЕ", sentence="Это (НЕ)ПРАВДА."))
    assert out == (
        "### Задание 13\n\nУкажите, как пишется частица **НЕ** в данном предложении."
        "\n\n---\n\n> Это (НЕ)ПРАВДА."
    )


def test_drill_result_correct_resolves_and_inline_explanation():
    out = _R.render_result(_F.drill_result(
        sentence="Это (НЕ)ПРАВДА.", answer="TOGETHER", user_answer="SEPARATE",
        explanation="Синоним.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** слитно")
    assert "> Это <u><b>НЕПРАВДА</b></u>." in out
    assert "Синоним." in out
    assert "<details" not in out


def test_drill_result_wrong_shows_opposite_display_struck():
    out = _R.render_result(_F.drill_result(
        sentence="Это (НЕ)ПРАВДА.", answer="TOGETHER", user_answer="SEPARATE",
        explanation="e", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~раздельно~~\n\n**Правильный ответ:** слитно")
