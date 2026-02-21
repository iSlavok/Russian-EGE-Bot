from pydantic import BaseModel


class Task8Content(BaseModel):
    """Контент для задания 8.

    sentence - текст предложения
    corrected_sentence - исправленное предложение с <u> подчёркиванием (только для ошибочных)
    """
    sentence: str
    corrected_sentence: str | None = None


class Task8ExamConfig(BaseModel):
    """Конфигурация для TASK_8_EXAM.

    exercise_ids - ID упражнений в порядке показа (1-9)
    error_type_order - 5 типов ошибок в порядке А-Д
    """
    exercise_ids: list[int]
    error_type_order: list[str]
