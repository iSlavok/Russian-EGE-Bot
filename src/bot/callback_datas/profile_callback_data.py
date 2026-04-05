from aiogram.filters.callback_data import CallbackData


class StatsCategoryCallbackData(CallbackData, prefix="sc"):
    category_id: int
