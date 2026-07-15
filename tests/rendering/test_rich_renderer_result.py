from app.rendering.rich_renderer import render_result
from app.schemas.rich_view import ResultView, AnswerLine, Quote, Collapsible, Paragraph


def test_result_correct_underlines_user_answer():
    r = ResultView(
        correct=True,
        answer=AnswerLine(label="Ответы", values=["в частности", "например"], user="например"),
    )
    out = render_result(r)
    assert out == "**✅ Верно**\n\n**Ответы:** в частности / <u>например</u>"


def test_result_wrong_shows_struck_user_and_correct():
    r = ResultView(
        correct=False,
        answer=AnswerLine(label="Правильный ответ", values=["вызвал"]),
        wrong_answer=AnswerLine(label="Ваш ответ", values=["создал"]),
        blocks=[Collapsible(summary="Объяснение", blocks=[Paragraph(text="почему")], open_if_wrong=True)],
    )
    out = render_result(r)
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~создал~~\n\n**Правильный ответ:** вызвал")
    assert "<details open><summary>Объяснение</summary>" in out
