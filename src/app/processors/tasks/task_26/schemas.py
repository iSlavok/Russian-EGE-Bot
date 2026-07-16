from pydantic import BaseModel


class Task26Content(BaseModel):
    """Контент для задания 26.

    task      - формулировка задания (средства связи предложений).
    sentences - фрагмент текста с нумерованными предложениями.
    """

    task: str
    sentences: str
