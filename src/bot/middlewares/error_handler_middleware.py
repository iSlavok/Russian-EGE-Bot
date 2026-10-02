from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import TelegramObject
from loguru import logger

from app.exceptions import (
    AppError,
    CategoryNotFoundError,
    ExerciseNotFoundError,
    InvalidCategoryStructureError,
    InvalidExerciseCountError,
    InvalidExerciseDataError,
    MissingTaskConfigError,
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
    ExerciseNotFoundError: "Задание не найдено. Выберите категорию заново.",
    InvalidExerciseCountError: "Не удалось собрать задание. Выберите категорию заново.",
    InvalidExerciseDataError: "Задание повреждено. Попробуйте другое.",
    MissingTaskConfigError: "Задание устарело. Выберите категорию заново.",
}

_GENERIC_APP_ERROR_MSG = "Произошла ошибка. Попробуйте ещё раз."
_UNEXPECTED_ERROR_MSG = "Произошла непредвиденная ошибка. Попробуйте позже."
_TELEGRAM_UNAVAILABLE_MSG = "Telegram сейчас не отвечает. Попробуйте через минуту."


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
            logger.warning("AppError handled: {!r}", exc)
            await self._notify(message_manager, self._message_for(exc))
        except (TelegramForbiddenError, TelegramNotFound) as exc:
            logger.info("Chat is unavailable to the bot: {}", exc.message)
        except TelegramRetryAfter as exc:
            logger.warning("Flood limit still active after retries: {}", exc.message)
        except (TelegramNetworkError, TelegramServerError) as exc:
            logger.warning("Telegram is unreachable: {!r}", exc)
            await self._notify(data.get("message_manager"), _TELEGRAM_UNAVAILABLE_MSG)
        except TelegramAPIError as exc:
            logger.warning("Telegram rejected the request: {}", exc.message)
            await self._notify(data.get("message_manager"), _UNEXPECTED_ERROR_MSG)
        except Exception as exc:
            message_manager = data.get("message_manager")
            if message_manager is None:
                raise
            logger.exception("Unexpected error: {!r}", exc)
            await self._notify(message_manager, _UNEXPECTED_ERROR_MSG)
        return None

    @staticmethod
    def _message_for(exc: AppError) -> str:
        """Текст для исключения: побеждает самый специфичный класс, а не порядок в словаре."""
        for exc_type in type(exc).__mro__:
            message = _ERROR_MESSAGES.get(exc_type)  # type: ignore[arg-type]
            if message is not None:
                return message
        return _GENERIC_APP_ERROR_MSG

    @staticmethod
    async def _notify(message_manager: "MessageManager | None", text: str) -> None:
        """Пытается сообщить юзеру об ошибке. Сама никогда не бросает.

        Иначе падение этой отправки (заблокированный чат, тот же flood limit)
        вылетает из middleware, и aiogram печатает второй трейс к уже залогированному.
        """
        if message_manager is None:
            return
        try:
            await message_manager.send_message(text=text)
        except TelegramAPIError as exc:
            logger.warning("Could not deliver the error message: {!r}", exc)
