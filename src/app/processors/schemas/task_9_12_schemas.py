from pydantic import BaseModel


class TaskN9N12Content(BaseModel):
    """Контент для заданий 9-12.

    word - слово с плейсхолдером {letter} для пропущенной буквы
    incorrect_letter - буква, которую можно ошибочно вставить
    context_before - контекст перед словом (необязательно)
    context_after - контекст после слова (необязательно)
    """
    word: str
    incorrect_letter: str
    context_before: str | None = None
    context_after: str | None = None


class TaskN9N12ExamConfig(BaseModel):
    """Конфигурация для TASK_9-12_EXAM.

    exercise_ids - ID упражнений в порядке: row0_word0, row0_word1, ..., row4_word_last
    correct_row_indices - индексы правильных рядов (0-4)
    words_per_row - количество слов в каждом ряду (2 или 3)
    """
    exercise_ids: list[int]
    correct_row_indices: list[int]
    words_per_row: int
