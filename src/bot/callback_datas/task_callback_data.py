from aiogram.filters.callback_data import CallbackData


class GetTaskCallbackData(CallbackData, prefix="get_task"):
    category_id: int


class SubmitAnswerCallbackData(CallbackData, prefix="submit_answer"):
    answer: str
