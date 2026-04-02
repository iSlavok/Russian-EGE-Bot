from pydantic import BaseModel


class Task25Content(BaseModel):
    """Контент для задания 25.

    task      - формулировка задания (e.g. «Из предложений 31–33 выпишите фразеологизм.»).
    sentences - фрагмент текста с нумерованными предложениями.
    """

    task: str
    sentences: str
