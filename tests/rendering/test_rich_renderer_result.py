from app.rendering.rich_renderer import RichRenderer
from app.schemas import ResultView, AnswerLine, Quote, Collapsible, Paragraph


def test_result_correct_underlines_user_answer():
    r = ResultView(
        correct=True,
        answer=AnswerLine(label="Ответы", values=["в частности", "например"], user="например"),
    )
    out = RichRenderer().render_result(r)
    assert out == "**✅ Верно**\n\n**Ответы:** в частности / <u>например</u>"


def test_result_wrong_shows_struck_user_and_correct():
    r = ResultView(
        correct=False,
        answer=AnswerLine(label="Правильный ответ", values=["вызвал"]),
        wrong_answer=AnswerLine(label="Ваш ответ", values=["создал"], strike=True),
        blocks=[Collapsible(summary="Объяснение", blocks=[Paragraph(text="почему")], open_if_wrong=True)],
    )
    out = RichRenderer().render_result(r)
    assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~создал~~\n\n**Правильный ответ:** вызвал")
    assert "<details open><summary>Объяснение</summary>" in out


def test_result_wrong_user_answer_not_struck_when_strike_false():
    r = ResultView(
        correct=False,
        answer=AnswerLine(label="Правильный ответ", values=["135"]),
        wrong_answer=AnswerLine(label="Ваш ответ", values=["12"], strike=False),
    )
    out = RichRenderer().render_result(r)
    assert out == "**❌ Неверно**\n\n**Ваш ответ:** 12\n\n**Правильный ответ:** 135"
