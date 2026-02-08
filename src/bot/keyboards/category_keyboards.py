from collections.abc import Iterable
from typing import cast

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.schemas import CategoryDTO
from bot.callback_datas import CategoryCallbackData, GetTaskCallbackData
from bot.keyboards.back_button import add_back_button


def get_categories_keyboard(
        categories: Iterable[CategoryDTO],
        current_category_id: int | None = None,
        *, row_width: int = 1,
        back_category_id: int | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=category.name, callback_data=CategoryCallbackData(category_id=category.id))
    if current_category_id is not None:
        builder.button(text="Все", callback_data=GetTaskCallbackData(category_id=current_category_id))

    keyboard = builder.adjust(row_width).as_markup()
    keyboard = cast("InlineKeyboardMarkup", keyboard)
    add_back_button(keyboard, back_category_id)
    return keyboard
