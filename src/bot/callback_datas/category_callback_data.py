from aiogram.filters.callback_data import CallbackData


class CategoryCallbackData(CallbackData, prefix="category"):
    category_id: int
