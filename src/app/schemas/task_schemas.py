from pydantic import BaseModel

from app.schemas.rich_view import ResultView, TaskView


class TaskOption(BaseModel):
    text: str
    value: str


class TaskUI(BaseModel):
    text: str | None = None
    text_continuation: str | None = None
    options: list[TaskOption] | None = None
    parse_mode: str = "HTML"
    options_per_row: int | list[int] = 1
    view: TaskView | None = None


class TaskResponse(BaseModel):
    task_ui: TaskUI
    exercise_ids: list[int] | int
    task_config: BaseModel | None = None


class CheckResult(BaseModel):
    is_correct: bool
    explanation: str | None
    result_view: ResultView | None = None
