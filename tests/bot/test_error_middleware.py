import pytest
from aiogram.types import TelegramObject
from unittest.mock import AsyncMock

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
from bot.middlewares.error_handler_middleware import (
    ErrorHandlerMiddleware,
    _ERROR_MESSAGES,
    _GENERIC_APP_ERROR_MSG,
    _UNEXPECTED_ERROR_MSG,
)


@pytest.fixture
def middleware():
    return ErrorHandlerMiddleware()


@pytest.fixture
def mock_mm():
    return AsyncMock()


def _make_handler(exc: Exception | None = None):
    async def handler(event, data):
        if exc is not None:
            raise exc
        return "ok"
    return handler


# ── Pass-through (no error) ──────────────────────────────────────────────────


async def test_pass_through(middleware, mock_mm):
    result = await middleware(
        _make_handler(), TelegramObject(), {"message_manager": mock_mm},
    )
    assert result == "ok"
    mock_mm.send_message.assert_not_called()


# ── Known AppError types (parametrized) ──────────────────────────────────────


@pytest.mark.parametrize(
    "exc, expected_msg",
    [
        (NoCategoryError(), _ERROR_MESSAGES[NoCategoryError]),
        (NoHandlerTypeError(), _ERROR_MESSAGES[NoHandlerTypeError]),
        (NoCurrentExercisesError(), _ERROR_MESSAGES[NoCurrentExercisesError]),
        (TaskForUserNotFoundError(user_id=1), _ERROR_MESSAGES[TaskForUserNotFoundError]),
        (CategoryNotFoundError(category_id=1), _ERROR_MESSAGES[CategoryNotFoundError]),
        (UserNotFoundError(user_id=1), _ERROR_MESSAGES[UserNotFoundError]),
        (ProcessorNotFoundError(handler_type="x"), _ERROR_MESSAGES[ProcessorNotFoundError]),
        (InvalidCategoryStructureError(), _ERROR_MESSAGES[InvalidCategoryStructureError]),
    ],
)
async def test_known_app_error(middleware, mock_mm, exc, expected_msg):
    await middleware(
        _make_handler(exc), TelegramObject(), {"message_manager": mock_mm},
    )
    mock_mm.send_message.assert_called_once()
    assert mock_mm.send_message.call_args.kwargs["text"] == expected_msg


# ── Unknown AppError subtype → generic message ──────────────────────────────


async def test_unknown_app_error_subtype(middleware, mock_mm):
    class CustomAppError(AppError):
        pass

    await middleware(
        _make_handler(CustomAppError("oops")),
        TelegramObject(),
        {"message_manager": mock_mm},
    )
    assert mock_mm.send_message.call_args.kwargs["text"] == _GENERIC_APP_ERROR_MSG


# ── Non-AppError Exception → unexpected message ─────────────────────────────


async def test_unexpected_exception(middleware, mock_mm):
    await middleware(
        _make_handler(RuntimeError("boom")),
        TelegramObject(),
        {"message_manager": mock_mm},
    )
    assert mock_mm.send_message.call_args.kwargs["text"] == _UNEXPECTED_ERROR_MSG


# ── message_manager=None → re-raise ─────────────────────────────────────────


async def test_app_error_reraise_without_mm(middleware):
    with pytest.raises(NoCategoryError):
        await middleware(
            _make_handler(NoCategoryError()), TelegramObject(), {},
        )


async def test_unexpected_error_reraise_without_mm(middleware):
    with pytest.raises(RuntimeError):
        await middleware(
            _make_handler(RuntimeError("boom")), TelegramObject(), {},
        )
