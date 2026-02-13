from pydantic import BaseModel


class TaskOption(BaseModel):
    text: str
    value: str


class TaskUI(BaseModel):
    text: str
    options: list[TaskOption] | None = None
    parse_mode: str = "HTML"


class TaskResponse(BaseModel):
    task_ui: TaskUI
    exercise_ids: list[int] | int
    task_config: BaseModel | None = None


class CheckResult(BaseModel):
    is_correct: bool
    explanation: str | None
