from pydantic import BaseModel


class Task5Paronym(BaseModel):
    """Пароним с объяснением и формой."""
    explanation: str
    inflected_form: str


class Task5Content(BaseModel):
    """Контент для задания 5.

    sentence - предложение с пропущенным словом (содержит {word} как placeholder)
    words - список паронимов (базовые формы)
    paronyms - список паронимов с их формами и объяснениями
    secondary_number - номер неправильного паронима для exam режима
    """
    sentence: str
    words: list[str]
    paronyms: list[Task5Paronym]
    secondary_number: int


class Task5ExamConfig(BaseModel):
    """Конфигурация для TASK_5_EXAM.

    Содержит информацию о том, какое предложение содержит ошибку.
    exercise_ids - ID упражнений в том порядке, как они показаны пользователю
    wrong_sentence_index - индекс предложения с неправильным словом (0-4)
    """
    exercise_ids: list[int]
    wrong_sentence_index: int
