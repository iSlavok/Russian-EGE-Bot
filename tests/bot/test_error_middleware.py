import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramServerError,
)
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
    _TELEGRAM_UNAVAILABLE_MSG,
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


# ── Telegram API errors: logged, never re-raised, never double-reported ──────


def _tg(exc_cls, message="boom", **kw):
    return exc_cls(method=None, message=message, **kw)


async def test_blocked_user_is_swallowed_without_notify(middleware, mock_mm):
    """Юзер заблокировал бота — рутинное событие, не повод для трейса и не повод писать в чат."""
    await middleware(
        _make_handler(_tg(TelegramForbiddenError, "Forbidden: bot was blocked by the user")),
        TelegramObject(),
        {"message_manager": mock_mm},
    )
    mock_mm.send_message.assert_not_called()


async def test_chat_not_found_is_swallowed(middleware, mock_mm):
    await middleware(
        _make_handler(_tg(TelegramNotFound, "Bad Request: chat not found")),
        TelegramObject(),
        {"message_manager": mock_mm},
    )
    mock_mm.send_message.assert_not_called()


async def test_retry_after_does_not_try_to_send(middleware, mock_mm):
    await middleware(
        _make_handler(_tg(TelegramRetryAfter, "Too Many Requests", retry_after=5)),
        TelegramObject(),
        {"message_manager": mock_mm},
    )
    mock_mm.send_message.assert_not_called()


@pytest.mark.parametrize("exc_cls", [TelegramNetworkError, TelegramServerError])
async def test_telegram_unavailable_notifies_user(middleware, mock_mm, exc_cls):
    await middleware(
        _make_handler(_tg(exc_cls, "timeout")), TelegramObject(), {"message_manager": mock_mm},
    )
    assert mock_mm.send_message.call_args.kwargs["text"] == _TELEGRAM_UNAVAILABLE_MSG


async def test_other_api_error_notifies_user(middleware, mock_mm):
    await middleware(
        _make_handler(_tg(TelegramBadRequest, "query is too old")),
        TelegramObject(),
        {"message_manager": mock_mm},
    )
    assert mock_mm.send_message.call_args.kwargs["text"] == _UNEXPECTED_ERROR_MSG


@pytest.mark.parametrize(
    "exc_cls",
    [TelegramForbiddenError, TelegramNotFound, TelegramNetworkError, TelegramServerError, TelegramBadRequest],
)
async def test_telegram_errors_never_reraise_without_mm(middleware, exc_cls):
    await middleware(_make_handler(_tg(exc_cls, "boom")), TelegramObject(), {})


async def test_failing_notify_does_not_escape(middleware):
    """Если отправка извинения тоже падает, исключение не должно вылетать наружу."""
    mm = AsyncMock()
    mm.send_message.side_effect = _tg(TelegramForbiddenError, "Forbidden: bot was blocked by the user")

    await middleware(
        _make_handler(RuntimeError("boom")), TelegramObject(), {"message_manager": mm},
    )
    mm.send_message.assert_awaited_once()


# ── Message lookup walks the MRO, not dict order ─────────────────────────────


async def test_most_specific_message_wins(middleware, mock_mm):
    class VerySpecificCategoryError(CategoryNotFoundError):
        pass

    await middleware(
        _make_handler(VerySpecificCategoryError(category_id=1)),
        TelegramObject(),
        {"message_manager": mock_mm},
    )
    assert mock_mm.send_message.call_args.kwargs["text"] == _ERROR_MESSAGES[CategoryNotFoundError]


@pytest.mark.parametrize("exc_type", sorted(_ERROR_MESSAGES, key=lambda c: c.__name__))
def test_every_mapped_error_is_an_app_error(exc_type):
    assert issubclass(exc_type, AppError)


def test_every_leaf_app_error_has_its_own_message():
    """Новое исключение без текста молча уедет в generic — пусть падает тест."""
    import inspect

    import app.exceptions as exceptions_module

    classes = {
        obj for _, obj in inspect.getmembers(exceptions_module, inspect.isclass)
        if issubclass(obj, AppError)
    }
    leaves = {c for c in classes if not any(issubclass(o, c) and o is not c for o in classes)}
    assert leaves <= set(_ERROR_MESSAGES)
