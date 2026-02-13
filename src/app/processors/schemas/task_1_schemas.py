from pydantic import BaseModel


class Task1Content(BaseModel):
    """Контент для задания 1.

    text - основной текст задания
    instruction - инструкция для пользователя
    """
    text: str
    instruction: str
