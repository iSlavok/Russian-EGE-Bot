from enum import StrEnum

from pydantic import BaseModel


class Task21TaskType(StrEnum):
    COMMA = "COMMA"
    DASH = "DASH"
    COLON = "COLON"


class Task21CommaRule(StrEnum):
    HOMOGENEOUS = "HOMOGENEOUS"
    MODIFIER = "MODIFIER"
    APPOSITION = "APPOSITION"
    ADVERBIAL = "ADVERBIAL"
    SUPPLEMENT = "SUPPLEMENT"
    COMPARISON = "COMPARISON"
    CLARIFICATION = "CLARIFICATION"
    SSP = "SSP"
    SPP = "SPP"
    BSP = "BSP"
    VOCATIVE = "VOCATIVE"
    PARENTHETICAL = "PARENTHETICAL"
    INTERJECTION = "INTERJECTION"
    DIRECT_SPEECH = "DIRECT_SPEECH"


class Task21DashRule(StrEnum):
    HOMOGENEOUS = "HOMOGENEOUS"
    SUBJ_PRED = "SUBJ_PRED"
    INCOMPLETE = "INCOMPLETE"
    APPOSITION = "APPOSITION"
    DIRECT_SPEECH = "DIRECT_SPEECH"
    BSP = "BSP"
    INSERTION = "INSERTION"
    CLARIFICATION = "CLARIFICATION"


class Task21ColonRule(StrEnum):
    BSP = "BSP"
    DIRECT_SPEECH = "DIRECT_SPEECH"
    HOMOGENEOUS = "HOMOGENEOUS"


class Task21DrillContent(BaseModel):
    """Контент для drill-режима задания 21.

    text      - одно предложение с нужным знаком препинания
    task_type - тип знака препинания
    """

    text: str
    task_type: Task21TaskType


class Task21ExamContent(BaseModel):
    """Контент для exam-режима задания 21.

    full_text   - пронумерованные предложения одним текстом
    task_type   - тип знака препинания
    answer_rule - правило, общее для всех answer-предложений
    """

    full_text: str
    task_type: Task21TaskType
    answer_rule: str
