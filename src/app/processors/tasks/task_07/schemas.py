from pydantic import BaseModel


class Task7Content(BaseModel):
    """Контент для задания 7.

    phrase - фраза с placeholder {word} для подстановки слова
    incorrect_answer - неправильная форма слова (может быть None)
    """
    phrase: str
    incorrect_answer: str | None = None


class Task7ExamConfig(BaseModel):
    """Конфигурация для TASK_7_EXAM.

    exercise_ids - ID упражнений в порядке показа пользователю
    wrong_phrase_index - индекс фразы с ошибкой (0-4)
    """
    exercise_ids: list[int]
    wrong_phrase_index: int
