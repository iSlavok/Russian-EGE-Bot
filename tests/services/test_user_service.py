import pytest

from app.enums import HandlerType
from app.exceptions import UserNotFoundError
from app.repositories import CategoryRepository, UserRepository
from app.schemas import CategoryDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.services.user_service import UserService


@pytest.fixture
def user_service(db_session, user_repository, category_repository):
    return UserService(
        session=db_session,
        user_repository=user_repository,
        category_repository=category_repository,
    )


class TestGetUserById:
    async def test_existing_user(self, user_service, user_factory):
        user = await user_factory(telegram_id=111)
        result = await user_service.get_user_by_id(user.id)
        assert result is not None
        assert result.telegram_id == 111

    async def test_nonexistent_user(self, user_service):
        result = await user_service.get_user_by_id(999_999)
        assert result is None


class TestGetUserByTelegram:
    async def test_creates_new_user(self, user_service):
        dto = await user_service.get_user_by_telegram(
            telegram_id=12345, tg_username="newuser", full_name="New User",
        )
        assert dto.telegram_id == 12345
        assert dto.username == "newuser"
        assert dto.full_name == "New User"
        assert dto.current_category is None
        assert dto.current_exercises is None

    async def test_existing_user_no_changes(self, user_service, user_factory):
        await user_factory(telegram_id=222, username="same", full_name="Same Name")
        dto = await user_service.get_user_by_telegram(
            telegram_id=222, tg_username="same", full_name="Same Name",
        )
        assert dto.telegram_id == 222
        assert dto.username == "same"

    async def test_existing_user_updates_username(self, user_service, user_factory):
        await user_factory(telegram_id=333, username="old_name", full_name="Name")
        dto = await user_service.get_user_by_telegram(
            telegram_id=333, tg_username="new_name", full_name="Name",
        )
        assert dto.username == "new_name"

    async def test_existing_user_updates_full_name(self, user_service, user_factory):
        await user_factory(telegram_id=444, username="user", full_name="Old Name")
        dto = await user_service.get_user_by_telegram(
            telegram_id=444, tg_username="user", full_name="New Name",
        )
        assert dto.full_name == "New Name"


class TestCreateUser:
    async def test_creates_and_returns(self, user_service):
        user = await user_service.create_user(
            telegram_id=555, tg_username="created", full_name="Created User",
        )
        assert user.id is not None
        assert user.telegram_id == 555
        assert user.username == "created"


class TestSelectCategory:
    async def test_happy_path(self, user_service, user_factory, category_factory):
        user_orm = await user_factory(telegram_id=666)
        cat_orm = await category_factory(name="Selected", handler_type=HandlerType.TASK_1_DRILL)

        user_dto = UserWithCategoryDTO(
            id=user_orm.id, telegram_id=666, username="u", full_name="U",
            exercise_started_at=None, current_category=None,
        )
        cat_dto = CategoryDTO(id=cat_orm.id, name="Selected", handler_type=HandlerType.TASK_1_DRILL, parent_id=None)

        await user_service.select_category(user_dto, cat_dto)

        assert user_dto.current_category_id == cat_orm.id
        assert user_dto.current_category == cat_dto

    async def test_user_not_found(self, user_service, category_factory):
        cat = await category_factory(name="Cat")
        user_dto = UserWithCategoryDTO(
            id=999_999, telegram_id=999, username=None, full_name="Ghost",
            exercise_started_at=None, current_category=None,
        )
        cat_dto = CategoryDTO(id=cat.id, name="Cat", handler_type=None, parent_id=None)

        with pytest.raises(UserNotFoundError):
            await user_service.select_category(user_dto, cat_dto)
