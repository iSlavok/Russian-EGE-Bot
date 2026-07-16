from unittest.mock import AsyncMock

import pytest

from app.enums import HandlerType
from app.exceptions import NoCategoryError, NoHandlerTypeError
from app.schemas import CategoryDTO
from app.schemas.user_schemas import UserWithCategoryDTO, UserWithExercisesDTO
from app.services.task_service import TaskService


@pytest.fixture
def mock_stats_service():
    svc = AsyncMock()
    svc.record_answer_stats = AsyncMock()
    return svc


@pytest.fixture
def task_service(processor_factory, user_repository, exercise_repository, mock_stats_service):
    return TaskService(
        processor_factory=processor_factory,
        user_repository=user_repository,
        exercise_repository=exercise_repository,
        stats_service=mock_stats_service,
    )


class TestStartTask:
    async def test_no_category_raises(self, task_service):
        user = UserWithCategoryDTO(
            id=1, telegram_id=1, username=None, full_name="U",
            exercise_started_at=None, current_category=None,
        )
        with pytest.raises(NoCategoryError):
            await task_service.start_task(user)

    async def test_no_handler_type_raises(self, task_service, category_factory):
        cat = await category_factory(name="No handler")
        cat_dto = CategoryDTO(id=cat.id, name="No handler", handler_type=None, parent_id=None)
        user = UserWithCategoryDTO(
            id=1, telegram_id=1, username=None, full_name="U",
            exercise_started_at=None, current_category=cat_dto,
        )
        with pytest.raises(NoHandlerTypeError):
            await task_service.start_task(user)

    async def test_happy_path(self, task_service, user_factory, category_factory, exercise_factory):
        cat = await category_factory(name="Task 1", handler_type=HandlerType.TASK_1_DRILL)
        await exercise_factory(
            category_id=cat.id,
            content={"text": "Прочитайте текст", "instruction": "Выберите ответ"},
            answer="42",
        )
        user = await user_factory(telegram_id=7777)
        user_dto = UserWithCategoryDTO(
            id=user.id, telegram_id=7777, username=None, full_name="U",
            exercise_started_at=None,
            current_category=CategoryDTO(id=cat.id, name="Task 1", handler_type=HandlerType.TASK_1_DRILL, parent_id=None),
        )

        task_ui = await task_service.start_task(user_dto)
        assert task_ui.view is not None


class TestCheckAnswer:
    async def test_no_category_raises(self, task_service):
        user = UserWithExercisesDTO(
            id=1, telegram_id=1, username=None, full_name="U",
            exercise_started_at=None, current_category=None,
        )
        with pytest.raises(NoCategoryError):
            await task_service.check_answer(user, "42")

    async def test_no_handler_type_raises(self, task_service, category_factory):
        cat = await category_factory(name="No handler")
        cat_dto = CategoryDTO(id=cat.id, name="No handler", handler_type=None, parent_id=None)
        user = UserWithExercisesDTO(
            id=1, telegram_id=1, username=None, full_name="U",
            exercise_started_at=None, current_category=cat_dto,
        )
        with pytest.raises(NoHandlerTypeError):
            await task_service.check_answer(user, "42")
