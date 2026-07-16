"""Юнит-тесты форматтера задания 8 (чистый, без БД): exam + drill."""
from app.processors.formatters import Task8Formatter, Task8Letter
from app.rendering.rich_renderer import RichRenderer

_F = Task8Formatter()
_R = RichRenderer()


def test_exam_condition_two_open_blocks_and_footer():
    out = _R.render_task(_F.condition(
        ["homogeneous_members_error", "participial_clause_error"],
        ["Предложение один", "Предложение два", "Предложение три"],
    ))
    assert out.startswith("### Задание 8\n\n")
    assert "<details open><summary>Грамматические ошибки</summary>" in out
    assert "> А) ошибка в построении предложения с однородными членами" in out
    assert "> Б) нарушение в построении предложения с причастным оборотом" in out
    assert "<details open><summary>Предложения</summary>" in out
    assert "1) Предложение один" in out
    assert out.endswith("_Запишите цифры для АБВГД._")


def test_exam_result_correct_letters_collapsed():
    letters = [Task8Letter(
        error_type="homogeneous_members_error", position=5, explanation="Объяснение А",
        sentence="Предложение пять", corrected_sentence="Исправлено пять", wrong=False,
    )]
    out = _R.render_result(_F.result(
        correct_answer="5", user_answer="5", letters=letters, sentences=["с1", "с2"], is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** 5")
    assert "<details><summary>А → 5. Однородные члены</summary>" in out
    assert "Объяснение А" in out
    assert "**Исходное предложение:**" in out
    assert "> Предложение пять" in out
    assert "**Правильное предложение:**" in out
    assert "> Исправлено пять" in out
    assert "<details><summary>Предложения</summary>" in out


def test_exam_result_wrong_opens_only_wrong_letters():
    letters = [
        Task8Letter("homogeneous_members_error", 5, "e", "s5", "c5", wrong=True),
        Task8Letter("participial_clause_error", 3, "e", "s3", None, wrong=False),
    ]
    out = _R.render_result(_F.result(
        correct_answer="53", user_answer="52", letters=letters, sentences=["a"], is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~52~~\n\n**Правильный ответ:** 53")
    assert "<details open><summary>А → 5. Однородные члены</summary>" in out
    assert "<details><summary>Б → 3. Причастный оборот</summary>" in out


def test_drill_condition_bold_instruction_and_quote():
    out = _R.render_task(_F.drill_condition("Предложение с ошибкой."))
    assert out == (
        "### Задание 8\n\n**Определите тип грамматической ошибки в предложении.**"
        "\n\n---\n\n> Предложение с ошибкой."
    )


def test_drill_result_correct_uses_short_label():
    out = _R.render_result(_F.drill_result(
        correct_type="homogeneous_members_error", user_type="homogeneous_members_error",
        explanation="Объ", sentence="s", corrected_sentence="c", is_correct=True,
    ))
    assert out.startswith("**✅ Верно**\n\n**Ответ:** Однородные члены")
    assert "<details><summary>Объяснение</summary>" in out


def test_drill_result_wrong_struck_and_open():
    out = _R.render_result(_F.drill_result(
        correct_type="homogeneous_members_error", user_type="participial_clause_error",
        explanation="Объ", sentence="s", corrected_sentence="c", is_correct=False,
    ))
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~Причастный оборот~~\n\n**Правильный ответ:** Однородные члены")
    assert "<details open><summary>Объяснение</summary>" in out


def test_drill_options_are_ten_error_types():
    options = Task8Formatter.drill_options()
    assert len(options) == 10
    assert all(option.text and option.value for option in options)
