from unittest.mock import AsyncMock

import pytest

from app.enums.category_enums import HandlerType
from app.exceptions import NoCategoryError, NoHandlerTypeError
from app.schemas import CategoryDTO, TaskOption, TaskUI, TaskView, UserWithExercisesDTO
from bot.handlers.task_handler import send_new_task


@pytest.fixture
def mock_mm():
    mm = AsyncMock()
    mm.send_rich.return_value = 1
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

    async def test_sends_rich_view_with_options(self, mock_mm):
        cat = CategoryDTO(id=1, name="Cat", handler_type=HandlerType.TASK_1_DRILL, parent_id=5)
        user = _make_user(category=cat)
        task_service = AsyncMock()
        task_service.start_task.return_value = TaskUI(
            view=TaskView(heading="Задание 1", instruction="Вопрос?"),
            options=[TaskOption(text="A", value="a")],
        )
        result = await send_new_task(user, task_service, mock_mm)
        assert result == 1
        mock_mm.send_rich.assert_called_once()
        mock_mm.send_message.assert_not_called()
