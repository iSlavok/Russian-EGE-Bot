from pydantic import BaseModel


class TaskOption(BaseModel):
    text: str
    value: str


class TaskUI(BaseModel):
    text: str
    options: list[TaskOption] | None = None
    parse_mode: str = "HTML"
    options_per_row: int | list[int] = 1


class TaskResponse(BaseModel):
    task_ui: TaskUI
    exercise_ids: list[int] | int
    task_config: BaseModel | None = None


class CheckResult(BaseModel):
    is_correct: bool
    explanation: str | None
