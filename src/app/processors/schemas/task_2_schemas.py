from pydantic import BaseModel


class Task2Content(BaseModel):
    """Контент для задания 2.

    text - текст с выделенным словом
    word_with_definition - слово с его лексическим определением
    """
    text: str
    word_with_definition: str
