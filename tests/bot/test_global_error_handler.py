from datetime import UTC, datetime

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramConflictError,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramServerError,
    TelegramUnauthorizedError,
)
from aiogram.types import Chat, Message, Update
from aiogram.types.error_event import ErrorEvent

from bot.middlewares import handle_unexpected_error


def _event(exc: Exception) -> ErrorEvent:
    update = Update(
        update_id=42,
        message=Message(message_id=1, date=datetime.now(UTC), chat=Chat(id=1, type="private")),
    )
    return ErrorEvent(update=update, exception=exc)


@pytest.mark.parametrize(
    "exc",
    [
        TelegramForbiddenError(method=None, message="bot was blocked by the user"),
        TelegramNotFound(method=None, message="chat not found"),
        TelegramRetryAfter(method=None, message="Too Many Requests", retry_after=3),
        TelegramNetworkError(method=None, message="timeout"),
        TelegramServerError(method=None, message="Bad Gateway"),
    ],
)
async def test_expected_errors_are_marked_handled(exc):
    assert await handle_unexpected_error(_event(exc)) is True


async def test_unknown_error_is_marked_handled():
    assert await handle_unexpected_error(_event(RuntimeError("boom"))) is True


async def test_other_api_error_is_marked_handled():
    exc = TelegramBadRequest(method=None, message="query is too old")
    assert await handle_unexpected_error(_event(exc)) is True


@pytest.mark.parametrize(
    "exc",
    [
        TelegramConflictError(method=None, message="terminated by other getUpdates request"),
        TelegramUnauthorizedError(method=None, message="Unauthorized"),
    ],
)
async def test_fatal_errors_are_not_swallowed(exc):
    """Два polling-инстанса или битый токен — чинить руками, глотать нельзя."""
    assert await handle_unexpected_error(_event(exc)) is False
