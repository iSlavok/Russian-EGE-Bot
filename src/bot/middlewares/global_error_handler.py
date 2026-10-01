from aiogram.exceptions import (
    TelegramConflictError,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramServerError,
    TelegramUnauthorizedError,
)
from aiogram.types.error_event import ErrorEvent
from loguru import logger

_EXPECTED: tuple[type[Exception], ...] = (
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramNetworkError,
    TelegramServerError,
)

_FATAL: tuple[type[Exception], ...] = (
    TelegramConflictError,
    TelegramUnauthorizedError,
)


async def handle_unexpected_error(event: ErrorEvent) -> bool:
    """Последняя сетка для исключений, не дошедших до ErrorHandlerMiddleware.

    Сюда попадает то, что упало во внешних middleware, фильтрах и при разборе
    апдейта, то есть до того, как у события появился message_manager. Без этого
    обработчика aiogram печатает дефолтный трейс на любую такую мелочь.
    """
    exc = event.exception
    update_id = event.update.update_id

    if isinstance(exc, _FATAL):
        logger.critical("Bot cannot keep polling (update {}): {!r}", update_id, exc)
        return False

    if isinstance(exc, _EXPECTED):
        logger.warning("{} on update {}: {}", type(exc).__name__, update_id, exc)
        return True

    logger.opt(exception=exc).error("Unhandled error on update {}: {!r}", update_id, exc)
    return True
