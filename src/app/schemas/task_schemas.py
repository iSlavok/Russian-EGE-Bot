from pydantic import BaseModel

from app.schemas.rich_view import ResultView, TaskView


class TaskOption(BaseModel):
    text: str
    value: str


class TaskUI(BaseModel):
    view: TaskView
    options: list[TaskOption] | None = None
    options_per_row: int | list[int] = 1


class TaskResponse(BaseModel):
    task_ui: TaskUI
    exercise_ids: list[int] | int
    task_config: BaseModel | None = None


class CheckResult(BaseModel):
    is_correct: bool
    result_view: ResultView
