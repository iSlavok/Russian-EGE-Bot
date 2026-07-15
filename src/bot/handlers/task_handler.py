from aiogram import Router
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NoCategoryError, NoHandlerTypeError
from app.rendering.rich_renderer import RichRenderer
from app.schemas import CheckResult, UserWithExercisesDTO
from app.services.category_service import CategoryService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.utils.text_utils import split_html_text
from bot.callback_datas import GetTaskCallbackData, SubmitAnswerCallbackData
from bot.keyboards import get_back_keyboard, get_task_options_keyboard
from bot.services import MessageManager

router = Router(name="task_router")
_renderer = RichRenderer()


async def _send_result(message_manager: MessageManager, text: str, *, use_edit: bool) -> None:
    """Отправляет текст результата, разбивая на 2 сообщения при превышении лимита TG."""
    parts = split_html_text(text)
    if len(parts) == 1:
        if use_edit:
            await message_manager.edit_message(text=text)
        else:
            await message_manager.send_message(text=text)
    else:
        if use_edit:
            await message_manager.edit_message(text=parts[0])
        else:
            await message_manager.send_message(text=parts[0])
        await message_manager.send_message(text=parts[1], clear_previous=False)


async def _send_check_result(message_manager: MessageManager, result: CheckResult, *, use_edit: bool) -> None:
    if result.result_view is not None:
        await message_manager.send_rich(_renderer.render_result(result.result_view), clear_previous=True)
        return
    response_text = "✅ Правильно!" if result.is_correct else "❌ Неправильно."
    if result.explanation:
        response_text += f"\n\n{result.explanation}"
    await _send_result(message_manager, response_text, use_edit=use_edit)


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
    logger.debug("User {} requested task for category_id={}", user.id, callback_data.category_id)
    await message_manager.edit_message(text="Загрузка задания...")
    categories = await category_service.get_by_id_with_tree(callback_data.category_id)
    await user_service.select_category(user=user, category=categories[0])
    parts_count = await send_new_task(
        user=user,
        task_service=task_service,
        message_manager=message_manager,
    )
    await message_manager.clear_messages(keep_bot_last=parts_count)
    await session.commit()
    await callback_query.answer()


async def send_new_task(user: UserWithExercisesDTO, task_service: TaskService, message_manager: MessageManager) -> int:
    if not user.current_category:
        raise NoCategoryError
    if not user.current_category.handler_type:
        raise NoHandlerTypeError
    task = await task_service.start_task(user)
    back_category_id = user.current_category.parent_id or 0
    keyboard = get_task_options_keyboard(
        task.options,
        back_category_id=back_category_id,
        row_width=task.options_per_row,
    ) if task.options else get_back_keyboard(back_category_id=back_category_id)
    if task.view is not None:
        await message_manager.send_rich(_renderer.render_task(task.view), reply_markup=keyboard, clear_previous=False)
        return 1
    text = task.text or ""
    if task.text_continuation:
        await message_manager.send_message(text=text, clear_previous=False)
        await message_manager.send_message(
            text=task.text_continuation,
            reply_markup=keyboard,
            clear_previous=False,
        )
        return 2
    await message_manager.send_message(
        text=text,
        reply_markup=keyboard,
        clear_previous=False,
    )
    return 1


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
    logger.debug("User {} submitted button answer: '{}'", user.id, callback_data.answer)
    result = await task_service.check_answer(user, callback_data.answer)
    await _send_check_result(message_manager, result, use_edit=True)
    await send_new_task(user, task_service, message_manager)
    await session.commit()
    await callback_query.answer()


@router.message()
async def submit_answer(
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
    logger.debug("User {} submitted text answer: '{}'", user.id, message.text)
    result = await task_service.check_answer(user, message.text)
    await _send_check_result(message_manager, result, use_edit=False)
    await send_new_task(user, task_service, message_manager)
    await session.commit()
