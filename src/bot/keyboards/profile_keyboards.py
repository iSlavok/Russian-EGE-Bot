from collections.abc import Sequence
from typing import cast

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.schemas.stats_schemas import CategoryStatItemDTO
from bot.callback_datas import StatsCategoryCallbackData


def get_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="profile_stats")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
    ])


def get_stats_categories_keyboard(
    items: Sequence[CategoryStatItemDTO],
    back_callback: str,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(
            text=item.name,
            callback_data=StatsCategoryCallbackData(category_id=item.category_id),
        )
    builder.adjust(1)
    keyboard = cast("InlineKeyboardMarkup", builder.as_markup())
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)],
    )
    return keyboard


def get_stats_back_keyboard(back_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)],
    ])
