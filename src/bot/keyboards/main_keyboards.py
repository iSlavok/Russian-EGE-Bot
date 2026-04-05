from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.back_button import add_back_button

MAIN_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="👉 Перейти к заданиям", callback_data="categories"),
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        ],
    ],
)


def get_back_keyboard(back_category_id: int | None = None) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    add_back_button(keyboard, back_category_id)
    return keyboard
