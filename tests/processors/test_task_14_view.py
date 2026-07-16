"""Юнит-тесты форматтера задания 14 (чистый, без БД): exam + drill."""
from app.processors.tasks.task_14 import Task14Formatter, Task14Sentence
from app.rendering.rich_renderer import RichRenderer

_F = Task14Formatter()
_R = RichRenderer()


def test_exam_condition_instruction_upper_and_quoted_sentences():
    out = _R.render_task(_F.condition(answer_type="TOGETHER", sentences=["(ЧТО)БЫ он пришёл.", "Смотри (В)ДАЛЬ."]))
    assert out.startswith("### Задание 14\n\n")
    assert "оба выделенных слова пишутся **СЛИТНО**" in out
    assert "\n\n---\n\n" in out
    assert "> 1) (ЧТО)БЫ он пришёл." in out
    assert "> 2) Смотри (В)ДАЛЬ." in out


def test_exam_result_correct_corrected_in_quote():
    sentences = [Task14Sentence(corrected_sentence="Чтобы он пришёл.", explanation="Союз чтобы.", wrong=False)]
    out = _R.render_result(_F.result(correct_answer="1", user_answer="1", sentences=sentences, is_correct=True))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 1")
    assert "<details><summary>Предложение 1</summary>" in out
    assert "> Чтобы он пришёл." in out
    assert "Союз чтобы." in out


def test_exam_result_wrong_opens_only_wrong():
    sentences = [
        Task14Sentence(corrected_sentence="c1", explanation="e", wrong=True),
        Task14Sentence(corrected_sentence="c2", explanation="e", wrong=False),
    ]
    out = _R.render_result(_F.result(correct_answer="2", user_answer="1", sentences=sentences, is_correct=False))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~1~~\n\n**Правильный ответ:** 2")
    assert "<details open><summary>Предложение 1</summary>" in out
    assert "<details><summary>Предложение 2</summary>" in out


def test_drill_condition_quote():
    out = _R.render_task(_F.drill_condition("Иду (ПО)ЗИМНЕМУ лесу."))
    assert out == "### Задание 14\n\nОпределите написание слова в скобках.\n\n---\n\n> Иду (ПО)ЗИМНЕМУ лесу."


def test_drill_result_resolves_prefix_bracket_hyphen():
    out = _R.render_result(_F.drill_result(
        sentence="Иду (ПО)ЗИМНЕМУ лесу.", answer="HYPHEN", user_answer="TOGETHER",
        explanation="Наречие.", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** через дефис")
    assert "> Иду <u><b>ПО-ЗИМНЕМУ</b></u> лесу." in out
    assert "Наречие." in out
    assert "<details" not in out


def test_drill_result_resolves_suffix_bracket_together():
    out = _R.render_result(_F.drill_result(
        sentence="Так ЧТО(БЫ) все ушли.", answer="TOGETHER", user_answer="SEPARATE",
        explanation="e", is_correct=True,
    ))
    assert "> Так <u><b>ЧТОБЫ</b></u> все ушли." in out


def test_drill_result_wrong_display_struck():
    out = _R.render_result(_F.drill_result(
        sentence="Иду (ПО)ЗИМНЕМУ лесу.", answer="HYPHEN", user_answer="TOGETHER",
        explanation="e", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~слитно~~\n\n**Правильный ответ:** через дефис")
