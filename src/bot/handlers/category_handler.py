from aiogram import F, Router
from aiogram.types import CallbackQuery
from dishka import FromDishka
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import UserWithExercisesDTO
from app.services.category_service import CategoryService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from bot.callback_datas import CategoryCallbackData
from bot.handlers.task_handler import send_new_task
from bot.keyboards import get_back_keyboard, get_categories_keyboard
from bot.services import MessageManager

router = Router(name="exercise_router")


@router.callback_query(F.data == "categories")
async def back_to_main_menu(
        callback_query: CallbackQuery,
        message_manager: MessageManager,
        category_service: FromDishka[CategoryService],
) -> None:
    categories = await category_service.get_root_categories()
    await message_manager.edit_message(text="Выберите задание", reply_markup=get_categories_keyboard(categories))
    await callback_query.answer()


@router.callback_query(CategoryCallbackData.filter())
async def category_callback(
        callback_query: CallbackQuery,
        user: UserWithExercisesDTO,
        message_manager: MessageManager,
        callback_data: CategoryCallbackData,
        session: FromDishka[AsyncSession],
        category_service: FromDishka[CategoryService],
        task_service: FromDishka[TaskService],
        user_service: FromDishka[UserService],
) -> None:
    category = await category_service.get_by_id_with_children(callback_data.category_id)
    if not category:
        await message_manager.edit_message(text="Категория не найдена", reply_markup=get_back_keyboard())
    if category.children:
        is_all_button = category.handler_type is not None
        await message_manager.edit_message(
            text="Выберите подкатегорию",
            reply_markup=get_categories_keyboard(
                category.children,
                current_category_id=category.id if is_all_button else None,
                back_category_id=category.parent_id or 0,
            ),
        )
    else:
        await message_manager.edit_message(text="Загрузка задания...")
        await user_service.select_category(user=user, category=category)
        await send_new_task(
            user=user,
            task_service=task_service,
            message_manager=message_manager,
        )
        await message_manager.clear_messages(keep_bot_last=1)
        await session.commit()
    await callback_query.answer()
