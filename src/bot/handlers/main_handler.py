from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import MAIN_KB
from bot.services import MessageManager

router = Router(name="exercise_router")


@router.callback_query(F.data == "main")
@router.message(Command("start", "menu"))
async def back_to_main_menu(
        event: CallbackQuery | Message,
        message_manager: MessageManager,
) -> None:
    await message_manager.edit_message(text="Главное меню", reply_markup=MAIN_KB)
    if isinstance(event, CallbackQuery):
        await event.answer()
