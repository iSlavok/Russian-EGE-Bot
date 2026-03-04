from pydantic import BaseModel


class Task15DrillContent(BaseModel):
    """Контент для drill-режима задания 15.

    sentence - фраза с плейсхолдером {n} вместо н/нн
    word     - только целевое слово с плейсхолдером {n}
    """

    sentence: str
    word: str


class Task15ExamContent(BaseModel):
    """Контент для exam-режима задания 15.

    sentence           - предложение с позиционными метками (1)(2)...
    corrected_sentence - предложение с расставленными н/нн
    modes              - доступные типы задания: ["Н"], ["НН"] или ["Н", "НН"]
    """

    sentence: str
    corrected_sentence: str
    modes: list[str]


class Task15ExamConfig(BaseModel):
    """Конфигурация для TASK_15_EXAM.

    mode - выбранный тип задания: "Н" или "НН"
    """

    mode: str
