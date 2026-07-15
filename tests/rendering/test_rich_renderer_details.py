from app.rendering.rich_renderer import render_block
from app.schemas.rich_view import Collapsible, Paragraph, Quote


def test_collapsible_collapsed_when_correct():
    c = Collapsible(summary="Объяснение", blocks=[Paragraph(text="почему")], open_if_wrong=True)
    out = render_block(c, correct=True, in_details=False)
    assert out == "<details><summary>Объяснение</summary>\n\nпочему\n\n</details>"


def test_collapsible_open_when_wrong():
    c = Collapsible(summary="Объяснение", blocks=[Paragraph(text="почему")], open_if_wrong=True)
    out = render_block(c, correct=False, in_details=False)
    assert out.startswith("<details open><summary>Объяснение</summary>")


def test_collapsible_quote_inside_uses_hard_break():
    c = Collapsible(summary="Текст", blocks=[Quote(lines=["a", "b"])], open=True)
    out = render_block(c, correct=True, in_details=False)
    assert "> a  \n> b" in out
