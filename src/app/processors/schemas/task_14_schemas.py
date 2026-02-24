from pydantic import BaseModel


class Task14DrillContent(BaseModel):
    """Контент для drill-режима задания 14.

    sentence - предложение с ОДНИМ выделенным словом в скобках,
               второе слово уже раскрыто.
    """

    sentence: str


class Task14ExamContent(BaseModel):
    """Контент для exam-режима задания 14.

    sentence           - предложение с ДВУМЯ выделенными словами в скобках
    corrected_sentence - предложение со всеми раскрытыми скобками
    types              - типы написания, которые встречались у этого предложения
                         в исходной базе (TOGETHER / SEPARATE / HYPHEN)
    """

    sentence: str
    corrected_sentence: str
    types: list[str]


class Task14ExamConfig(BaseModel):
    """Конфигурация для TASK_14_EXAM.

    exercise_ids    - ID упражнений в порядке отображения (5 штук)
    correct_indices - 0-based индексы «правильных» предложений
    answer_type     - тип, который искали: TOGETHER / SEPARATE / HYPHEN
    """

    exercise_ids: list[int]
    correct_indices: list[int]
    answer_type: str
