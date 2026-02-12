from pydantic import BaseModel


class Task4Content(BaseModel):
    word: str
    incorrect_stress: int
    context_before: str | None = None
    context_after: str | None = None


class Task4ExamConfig(BaseModel):
    """Конфигурация для TASK_4_EXAM.

    Содержит информацию о том, где в UI расставлены ударения в словах.
    exercise_ids - ID упражнений в том порядке, как они показаны пользователю
    stress_positions - список позиций ударений для каждого слова.
    Например: [2, 1, 3, 2, 1] означает что в первом слове ударение на 2-й букве,
    во втором на 1-й и т.д.
    """
    exercise_ids: list[int]
    stress_positions: list[int]
