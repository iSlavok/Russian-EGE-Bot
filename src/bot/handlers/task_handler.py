from aiogram import Router
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import UserWithExercisesDTO
from app.services.category_service import CategoryService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from bot.callback_datas import GetTaskCallbackData, SubmitAnswerCallbackData
from bot.keyboards import get_back_keyboard, get_task_options_keyboard
from bot.services import MessageManager

router = Router(name="task_router")


@router.callback_query(GetTaskCallbackData.filter())
async def get_task(
        user: UserWithExercisesDTO,
        callback_query: CallbackQuery,
        callback_data: GetTaskCallbackData,
        message_manager: MessageManager,
        session: FromDishka[AsyncSession],
        task_service: FromDishka[TaskService],
        user_service: FromDishka[UserService],
        category_service: FromDishka[CategoryService],
) -> None:
    await message_manager.edit_message(text="Загрузка задания...")
    categories = await category_service.get_by_id_with_tree(callback_data.category_id)
    await user_service.select_category(user=user, category=categories[0])
    await send_new_task(
        user=user,
        task_service=task_service,
        message_manager=message_manager,
    )
    await message_manager.clear_messages(keep_bot_last=1)
    await session.commit()
    await callback_query.answer()


async def send_new_task(user: UserWithExercisesDTO, task_service: TaskService, message_manager: MessageManager) -> None:
    if not user.current_category:
        msg = "User does not have a current category set."
        raise ValueError(msg)
    if not user.current_category.handler_type:
        msg = "Current category does not have a handler type defined."
        raise ValueError(msg)
    task = await task_service.start_task(user)
    back_category_id = user.current_category.parent_id or 0
    keyboard = get_task_options_keyboard(task.options, back_category_id=back_category_id) \
        if task.options else get_back_keyboard(back_category_id=back_category_id)
    await message_manager.send_message(
        text=task.text,
        reply_markup=keyboard,
        clear_previous=False,
    )


@router.callback_query(SubmitAnswerCallbackData.filter())
async def submit_answer_button(
        callback_query: CallbackQuery,
        user: UserWithExercisesDTO,
        callback_data: SubmitAnswerCallbackData,
        message_manager: MessageManager,
        session: FromDishka[AsyncSession],
        task_service: FromDishka[TaskService],
) -> None:
    await message_manager.clear_messages(keep_bot_last=1)
    result = await task_service.check_answer(user, callback_data.answer)
    response_text = "✅ Правильно!" if result.is_correct else "❌ Неправильно."
    if result.explanation:
        response_text += f"\n\n{result.explanation}"
    await message_manager.edit_message(text=response_text)
    await send_new_task(user, task_service, message_manager)
    await session.commit()
    await callback_query.answer()


@router.message()
async def sumit_answer(
        message: Message,
        user: UserWithExercisesDTO,
        message_manager: MessageManager,
        session: FromDishka[AsyncSession],
        task_service: FromDishka[TaskService],
) -> None:
    if not user.current_exercises:
        await message_manager.send_message(text="У вас нет активных заданий. Выберите категорию, чтобы начать.")
        return
    if message.text is None:
        await message_manager.send_message(text="Пожалуйста, отправьте текстовый ответ.")
        return
    await message_manager.clear_messages(keep_bot_last=1)
    result = await task_service.check_answer(user, message.text)
    response_text = "✅ Правильно!" if result.is_correct else "❌ Неправильно."
    if result.explanation:
        response_text += f"\n\n{result.explanation}"
    await message_manager.send_message(text=response_text)
    await send_new_task(user, task_service, message_manager)
    await session.commit()
