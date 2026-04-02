from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from loguru import logger

from app.exceptions import (
    AppError,
    CategoryNotFoundError,
    InvalidCategoryStructureError,
    NoCategoryError,
    NoCurrentExercisesError,
    NoHandlerTypeError,
    ProcessorNotFoundError,
    TaskForUserNotFoundError,
    UserNotFoundError,
)

if TYPE_CHECKING:
    from bot.services import MessageManager

_ERROR_MESSAGES: dict[type[AppError], str] = {
    NoCategoryError: "Категория не выбрана. Выберите категорию, чтобы начать.",
    NoHandlerTypeError: "Для данной категории пока нет заданий.",
    NoCurrentExercisesError: "У вас нет активных заданий. Выберите категорию, чтобы начать.",
    TaskForUserNotFoundError: "К сожалению, задания для данной категории закончились. Попробуйте другую.",
    CategoryNotFoundError: "Категория не найдена.",
    UserNotFoundError: "Произошла ошибка. Попробуйте /start.",
    ProcessorNotFoundError: "Данный тип задания пока не поддерживается.",
    InvalidCategoryStructureError: "Ошибка структуры категории. Попробуйте другую.",
}

_GENERIC_APP_ERROR_MSG = "Произошла ошибка. Попробуйте ещё раз."
_UNEXPECTED_ERROR_MSG = "Произошла непредвиденная ошибка. Попробуйте позже."


class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:  # noqa: ANN401
        try:
            return await handler(event, data)
        except AppError as exc:
            message_manager: MessageManager | None = data.get("message_manager")
            if message_manager is None:
                raise
            logger.warning(f"AppError handled: {exc!r}")
            user_msg = next(
                (msg for exc_type, msg in _ERROR_MESSAGES.items() if isinstance(exc, exc_type)),
                _GENERIC_APP_ERROR_MSG,
            )
            await message_manager.send_message(text=user_msg)
        except Exception as exc:
            message_manager: MessageManager | None = data.get("message_manager")
            if message_manager is None:
                raise
            logger.exception(f"Unexpected error: {exc!r}")
            await message_manager.send_message(text=_UNEXPECTED_ERROR_MSG)
