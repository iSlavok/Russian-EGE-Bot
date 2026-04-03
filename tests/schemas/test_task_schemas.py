from pydantic import BaseModel

from app.schemas.task_schemas import CheckResult, TaskOption, TaskResponse, TaskUI


class TestTaskOption:
    def test_creation(self):
        opt = TaskOption(text="Вариант А", value="a")
        assert opt.text == "Вариант А"
        assert opt.value == "a"

    def test_serialization(self):
        opt = TaskOption(text="test", value="1")
        data = opt.model_dump()
        assert data == {"text": "test", "value": "1"}


class TestTaskUI:
    def test_minimal(self):
        ui = TaskUI(text="Вопрос")
        assert ui.text == "Вопрос"
        assert ui.text_continuation is None
        assert ui.options is None
        assert ui.parse_mode == "HTML"
        assert ui.options_per_row == 1

    def test_with_options(self):
        opts = [TaskOption(text="A", value="1"), TaskOption(text="B", value="2")]
        ui = TaskUI(text="Выберите:", options=opts)
        assert len(ui.options) == 2
        assert ui.options[0].text == "A"

    def test_with_continuation(self):
        ui = TaskUI(text="Часть 1", text_continuation="Часть 2")
        assert ui.text_continuation == "Часть 2"

    def test_options_per_row_list(self):
        ui = TaskUI(text="Q", options_per_row=[2, 3])
        assert ui.options_per_row == [2, 3]

    def test_parse_mode_default(self):
        ui = TaskUI(text="Q")
        assert ui.parse_mode == "HTML"


class TestTaskResponse:
    def test_single_exercise_id(self):
        ui = TaskUI(text="Q")
        resp = TaskResponse(task_ui=ui, exercise_ids=42)
        assert resp.exercise_ids == 42
        assert resp.task_config is None

    def test_multiple_exercise_ids(self):
        ui = TaskUI(text="Q")
        resp = TaskResponse(task_ui=ui, exercise_ids=[1, 2, 3])
        assert resp.exercise_ids == [1, 2, 3]

    def test_with_task_config(self):
        class MyConfig(BaseModel):
            key: str = "val"

        ui = TaskUI(text="Q")
        cfg = MyConfig()
        resp = TaskResponse(task_ui=ui, exercise_ids=1, task_config=cfg)
        assert resp.task_config.key == "val"


class TestCheckResult:
    def test_correct(self):
        r = CheckResult(is_correct=True, explanation=None)
        assert r.is_correct is True
        assert r.explanation is None

    def test_incorrect_with_explanation(self):
        r = CheckResult(is_correct=False, explanation="Правильный ответ: 42")
        assert r.is_correct is False
        assert "42" in r.explanation

    def test_serialization_roundtrip(self):
        r = CheckResult(is_correct=True, explanation="ok")
        data = r.model_dump()
        r2 = CheckResult(**data)
        assert r == r2
