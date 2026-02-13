from typing import cast

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.schemas import TaskOption
from bot.callback_datas import SubmitAnswerCallbackData
from bot.keyboards.back_button import add_back_button


def get_task_options_keyboard(
        options: list[TaskOption],
        back_category_id: int,
        row_width: int = 1,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in options:
        style = None
        if option.value == "true":
            style = "success"
        elif option.value == "false":
            style = "danger"
        builder.button(
            text=option.text,
            callback_data=SubmitAnswerCallbackData(answer=option.value),
            style=style,
        )
    keyboard = builder.adjust(row_width).as_markup()
    keyboard = cast("InlineKeyboardMarkup", keyboard)
    add_back_button(keyboard, back_category_id)
    return keyboard
