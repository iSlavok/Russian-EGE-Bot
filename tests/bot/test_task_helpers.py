from unittest.mock import AsyncMock, patch

import pytest

from app.enums.category_enums import HandlerType
from app.exceptions import NoCategoryError, NoHandlerTypeError
from app.schemas import CategoryDTO, TaskOption, TaskUI, UserWithExercisesDTO
from bot.handlers.task_handler import _send_result, send_new_task


@pytest.fixture
def mock_mm():
    mm = AsyncMock()
    mm.send_message.return_value = None
    mm.edit_message.return_value = None
    return mm


def _make_user(
    *,
    category: CategoryDTO | None = None,
    exercises: list | None = None,
) -> UserWithExercisesDTO:
    return UserWithExercisesDTO(
        id=1,
        telegram_id=1000,
        username="test",
        full_name="Test User",
        exercise_started_at=None,
        current_category=category,
        current_exercises=exercises,
    )


# ── _send_result ─────────────────────────────────────────────────────────────


class TestSendResult:
    async def test_short_text_edit(self, mock_mm):
        with patch("bot.handlers.task_handler.split_html_text", return_value=["short"]):
            await _send_result(mock_mm, "short", use_edit=True)
        mock_mm.edit_message.assert_called_once_with(text="short")
        mock_mm.send_message.assert_not_called()

    async def test_short_text_send(self, mock_mm):
        with patch("bot.handlers.task_handler.split_html_text", return_value=["short"]):
            await _send_result(mock_mm, "short", use_edit=False)
        mock_mm.send_message.assert_called_once_with(text="short")
        mock_mm.edit_message.assert_not_called()

    async def test_long_text_edit(self, mock_mm):
        with patch("bot.handlers.task_handler.split_html_text", return_value=["part1", "part2"]):
            await _send_result(mock_mm, "long", use_edit=True)
        mock_mm.edit_message.assert_called_once_with(text="part1")
        mock_mm.send_message.assert_called_once_with(text="part2", clear_previous=False)

    async def test_long_text_send(self, mock_mm):
        with patch("bot.handlers.task_handler.split_html_text", return_value=["part1", "part2"]):
            await _send_result(mock_mm, "long", use_edit=False)
        assert mock_mm.send_message.call_count == 2
        mock_mm.send_message.assert_any_call(text="part1")
        mock_mm.send_message.assert_any_call(text="part2", clear_previous=False)


# ── send_new_task ────────────────────────────────────────────────────────────


class TestSendNewTask:
    async def test_no_category_raises(self, mock_mm):
        user = _make_user(category=None)
        with pytest.raises(NoCategoryError):
            await send_new_task(user, AsyncMock(), mock_mm)

    async def test_no_handler_type_raises(self, mock_mm):
        cat = CategoryDTO(id=1, name="Cat", handler_type=None, parent_id=None)
        user = _make_user(category=cat)
        with pytest.raises(NoHandlerTypeError):
            await send_new_task(user, AsyncMock(), mock_mm)

    async def test_happy_path_single_part(self, mock_mm):
        cat = CategoryDTO(id=1, name="Cat", handler_type=HandlerType.TASK_1_DRILL, parent_id=5)
        user = _make_user(category=cat)
        task_service = AsyncMock()
        task_service.start_task.return_value = TaskUI(
            text="Question?",
            options=[TaskOption(text="A", value="a")],
        )
        result = await send_new_task(user, task_service, mock_mm)
        assert result == 1
        mock_mm.send_message.assert_called_once()

    async def test_happy_path_two_parts(self, mock_mm):
        cat = CategoryDTO(id=1, name="Cat", handler_type=HandlerType.TASK_1_DRILL, parent_id=5)
        user = _make_user(category=cat)
        task_service = AsyncMock()
        task_service.start_task.return_value = TaskUI(
            text="Part 1",
            text_continuation="Part 2",
            options=[TaskOption(text="A", value="a")],
        )
        result = await send_new_task(user, task_service, mock_mm)
        assert result == 2
        assert mock_mm.send_message.call_count == 2
