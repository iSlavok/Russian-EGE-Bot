from pydantic import BaseModel


class Task2324Content(BaseModel):
    """Контент для заданий 23 и 24.

    text    - полный текст с нумерованными предложениями.
    options - 5 утверждений к тексту.
    """

    text: str
    options: list[str]


class Task2324Config(BaseModel):
    """Конфиг задачи для заданий 23 и 24.

    correct_digits - цифры правильных вариантов из БД (e.g. «123»).
    ask_incorrect  - True → спрашиваем НЕверные/несоответствующие утверждения.
    """

    correct_digits: str
    ask_incorrect: bool
