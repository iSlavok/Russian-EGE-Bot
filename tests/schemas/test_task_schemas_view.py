from app.schemas.task_schemas import TaskUI, CheckResult
from app.schemas import TaskView, ResultView, AnswerLine


def test_taskui_view_defaults_none():
    ui = TaskUI(text="hi")
    assert ui.view is None


def test_taskui_accepts_view():
    ui = TaskUI(text="hi", view=TaskView(heading="Задание 1", instruction="i"))
    assert ui.view.heading == "Задание 1"


def test_checkresult_result_view():
    r = CheckResult(
        is_correct=True,
        explanation=None,
        result_view=ResultView(correct=True, answer=AnswerLine(label="Ответ", values=["x"])),
    )
    assert r.result_view.correct is True
