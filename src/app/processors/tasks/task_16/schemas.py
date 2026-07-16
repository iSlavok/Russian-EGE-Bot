from pydantic import BaseModel


class Task16Content(BaseModel):
    """Контент для drill и exam режимов задания 16.

    sentence           - предложение без запятых
    corrected_sentence - предложение с расставленными запятыми
    """

    sentence: str
    corrected_sentence: str


class Task16ExamConfig(BaseModel):
    """Конфигурация для TASK_16_EXAM.

    exercise_ids    - id упражнений в порядке показа пользователю
    correct_indices - 0-индексированные позиции, где нужна ровно одна запятая
    """

    exercise_ids: list[int]
    correct_indices: list[int]
