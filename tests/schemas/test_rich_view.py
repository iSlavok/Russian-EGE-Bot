# tests/schemas/test_rich_view.py
from app.schemas.rich_view import (
    Paragraph, Divider, Quote, NumberedList, Collapsible,
    TaskView, AnswerLine, ResultView,
)


def test_taskview_holds_blocks():
    v = TaskView(
        heading="Задание 1",
        instruction="Подберите слово.",
        blocks=[Divider(), Quote(lines=["текст"])],
    )
    assert v.heading == "Задание 1"
    assert v.blocks[0].kind == "divider"
    assert v.blocks[1].lines == ["текст"]


def test_collapsible_nests_blocks():
    c = Collapsible(summary="Объяснение", blocks=[Paragraph(text="почему")], open_if_wrong=True)
    assert c.kind == "collapsible"
    assert c.open is False
    assert c.open_if_wrong is True
    assert c.blocks[0].text == "почему"


def test_resultview_answer():
    r = ResultView(
        correct=True,
        answer=AnswerLine(label="Ответ", values=["в частности", "например"], user="например"),
        blocks=[NumberedList(items=["a", "b"])],
    )
    assert r.correct is True
    assert r.answer.user == "например"
    assert r.blocks[0].items == ["a", "b"]
