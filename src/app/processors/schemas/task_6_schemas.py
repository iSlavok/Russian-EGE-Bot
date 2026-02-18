from enum import StrEnum

from pydantic import BaseModel


class Task6Type(StrEnum):
    """Типы заданий для задания 6."""

    REMOVE = "REMOVE"
    REPLACE = "REPLACE"


class Task6Content(BaseModel):
    """Контент для задания 6.

    sentence - предложение с лексической ошибкой
    task_type - тип задания (REMOVE или REPLACE)
    sentence_with_markup - предложение с подчеркиванием слова для замены/удаления
    corrected_sentence - исправленное предложение (с подчеркиванием нового слова для REPLACE)
    """

    sentence: str
    task_type: Task6Type
    sentence_with_markup: str
    corrected_sentence: str
