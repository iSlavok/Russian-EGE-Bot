from pydantic import BaseModel


class TaskN17N20Content(BaseModel):
    """Контент для заданий 17–20 (расстановка запятых).

    sentence           - предложение с позиционными метками (1)(2)...
    correct_sentence   - предложение с расставленными запятыми
    """

    sentence: str
    correct_sentence: str
