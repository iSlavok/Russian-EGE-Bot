from pydantic import BaseModel


class Task13Content(BaseModel):
    """Контент для задания 13 (НЕ/НИ слитно/раздельно).

    sentence  - предложение с частицей в формате (НЕ)СЛОВО или (НИ)СЛОВО
    particle  - какая частица в предложении: 'НЕ' или 'НИ'
    """

    sentence: str
    particle: str


class Task13ExamConfig(BaseModel):
    """Конфигурация для TASK_13_EXAM.

    exercise_ids    - ID упражнений в порядке отображения (5 штук)
    correct_indices - 0-based индексы «правильных» предложений
    answer_type     - что искали: 'TOGETHER' или 'SEPARATE'
    mode            - режим задачи: 'НЕ' или 'НЕ/НИ'
    """

    exercise_ids: list[int]
    correct_indices: list[int]
    answer_type: str
    mode: str
