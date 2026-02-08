from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.callback_datas import CategoryCallbackData


def add_back_button(
    keyboard: InlineKeyboardMarkup,
    back_category_id: int | None = None,
) -> None:
    """
    Мутирует (изменяет) исходный объект клавиатуры, добавляя кнопку в конец.
    Ничего не возвращает.
    """
    if back_category_id is not None:
        if back_category_id > 0:
            callback_data = CategoryCallbackData(category_id=back_category_id).pack()
        else:
            callback_data = "categories"
    else:
        callback_data = "main"
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)],
    )
