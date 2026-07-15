# tests/bot/test_task_handler_rich.py
# Реально тестируем ветку хендлера: при task.view хендлер зовёт message_manager.send_rich
# (а не send_message). Паттерн из tests/bot/test_task_helpers.py (mock_mm = AsyncMock).
from unittest.mock import AsyncMock

from app.enums.category_enums import HandlerType
from app.schemas import CategoryDTO, TaskUI, UserWithExercisesDTO
from app.schemas.rich_view import Quote, TaskView
from bot.handlers.task_handler import send_new_task


def _user(category):
    return UserWithExercisesDTO(
        id=1, telegram_id=1000, username="t", full_name="T",
        exercise_started_at=None, current_category=category, current_exercises=None,
    )


async def test_send_new_task_uses_send_rich_when_view_present():
    cat = CategoryDTO(id=1, name="Cat", handler_type=HandlerType.TASK_1_DRILL, parent_id=5)
    mm = AsyncMock()
    task_service = AsyncMock()
    task_service.start_task.return_value = TaskUI(
        text="fallback",
        view=TaskView(heading="Задание 1", instruction="i", blocks=[Quote(lines=["x"])]),
    )
    result = await send_new_task(_user(cat), task_service, mm)
    assert result == 1
    mm.send_rich.assert_called_once()
    mm.send_message.assert_not_called()


async def test_send_new_task_uses_send_message_when_no_view():
    cat = CategoryDTO(id=1, name="Cat", handler_type=HandlerType.TASK_1_DRILL, parent_id=5)
    mm = AsyncMock()
    task_service = AsyncMock()
    task_service.start_task.return_value = TaskUI(text="Q")
    await send_new_task(_user(cat), task_service, mm)
    mm.send_message.assert_called_once()
    mm.send_rich.assert_not_called()


async def test_send_new_task_falls_back_to_html_when_send_rich_fails():
    cat = CategoryDTO(id=1, name="Cat", handler_type=HandlerType.TASK_1_DRILL, parent_id=5)
    mm = AsyncMock()
    mm.send_rich.side_effect = RuntimeError("boom")
    task_service = AsyncMock()
    task_service.start_task.return_value = TaskUI(
        text="fallback",
        view=TaskView(heading="Задание 1", instruction="i", blocks=[Quote(lines=["x"])]),
    )
    result = await send_new_task(_user(cat), task_service, mm)
    assert result == 1
    mm.send_rich.assert_called_once()
    mm.send_message.assert_called_once()
