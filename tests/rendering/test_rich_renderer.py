from app.rendering.rich_renderer import render_task
from app.schemas.rich_view import TaskView, Divider, Quote, NumberedList


def test_render_task_heading_instruction_divider_quote():
    v = TaskView(
        heading="Задание 1",
        instruction="Подберите слово.",
        blocks=[Quote(lines=["Первое предложение.", "Второе."])],
    )
    out = render_task(v)
    assert out == (
        "### Задание 1\n\n"
        "Подберите слово.\n\n"
        "---\n\n"
        "> Первое предложение.\n> Второе."
    )


def test_render_task_numbered_list_quoted_and_footer():
    v = TaskView(
        heading="Задание 5",
        instruction="Инструкция.",
        blocks=[NumberedList(items=["раз", "два"], quoted=True)],
        footer="Запишите номера.",
    )
    out = render_task(v)
    assert "> 1. раз\n> 2. два" in out
    assert out.endswith("_Запишите номера._")
