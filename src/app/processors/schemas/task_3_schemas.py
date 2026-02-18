from pydantic import BaseModel


class Task3Content(BaseModel):
    """Контент для задания 3.

    text - основной текст фрагмента
    statements - список из 5 утверждений для оценки
    """

    text: str
    statements: list[str]
