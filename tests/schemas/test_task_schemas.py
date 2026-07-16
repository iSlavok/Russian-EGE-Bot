import pytest
from pydantic import BaseModel, ValidationError

from app.schemas import AnswerLine, ResultView, TaskView
from app.schemas.task_schemas import CheckResult, TaskOption, TaskResponse, TaskUI


def _view() -> TaskView:
    return TaskView(heading="Задание 1", instruction="Вопрос?")


class TestTaskOption:
    def test_creation(self):
        opt = TaskOption(text="Вариант А", value="a")
        assert opt.text == "Вариант А"
        assert opt.value == "a"

    def test_serialization(self):
        opt = TaskOption(text="test", value="1")
        assert opt.model_dump() == {"text": "test", "value": "1"}


class TestTaskUI:
    def test_view_is_required(self):
        with pytest.raises(ValidationError):
            TaskUI()

    def test_minimal(self):
        ui = TaskUI(view=_view())
        assert ui.view.heading == "Задание 1"
        assert ui.options is None
        assert ui.options_per_row == 1

    def test_with_options(self):
        opts = [TaskOption(text="A", value="1"), TaskOption(text="B", value="2")]
        ui = TaskUI(view=_view(), options=opts, options_per_row=[2, 3])
        assert len(ui.options) == 2
        assert ui.options[0].text == "A"
        assert ui.options_per_row == [2, 3]


class TestTaskResponse:
    def test_single_exercise_id(self):
        resp = TaskResponse(task_ui=TaskUI(view=_view()), exercise_ids=42)
        assert resp.exercise_ids == 42
        assert resp.task_config is None

    def test_multiple_exercise_ids(self):
        resp = TaskResponse(task_ui=TaskUI(view=_view()), exercise_ids=[1, 2, 3])
        assert resp.exercise_ids == [1, 2, 3]

    def test_with_task_config(self):
        class MyConfig(BaseModel):
            key: str = "val"

        resp = TaskResponse(task_ui=TaskUI(view=_view()), exercise_ids=1, task_config=MyConfig())
        assert resp.task_config.key == "val"


class TestCheckResult:
    def test_result_view_is_required(self):
        with pytest.raises(ValidationError):
            CheckResult(is_correct=True)

    def test_carries_result_view(self):
        r = CheckResult(
            is_correct=True,
            result_view=ResultView(correct=True, answer=AnswerLine(label="Ответ", values=["42"])),
        )
        assert r.is_correct is True
        assert r.result_view.correct is True

    def test_serialization_roundtrip(self):
        r = CheckResult(is_correct=False, result_view=ResultView(correct=False))
        r2 = CheckResult(**r.model_dump())
        assert r == r2
