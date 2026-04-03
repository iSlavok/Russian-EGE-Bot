import pytest


class TestGetByTelegramIdWithExercises:
    async def test_returns_user(self, user_repository, user_factory):
        user = await user_factory(telegram_id=111)

        result = await user_repository.get_by_telegram_id_with_exercises(111)

        assert result is not None
        assert result.id == user.id
        assert result.telegram_id == 111

    async def test_nonexistent_telegram_id(self, user_repository):
        result = await user_repository.get_by_telegram_id_with_exercises(999_999)
        assert result is None

    async def test_loads_empty_exercises(self, user_repository, user_factory):
        await user_factory(telegram_id=222)

        result = await user_repository.get_by_telegram_id_with_exercises(222)

        assert result is not None
        assert result.current_exercises == []

    async def test_loads_current_category(
        self, user_repository, user_factory, category_factory, db_session,
    ):
        category = await category_factory(name="Math")
        user = await user_factory(telegram_id=333)
        user.current_category_id = category.id
        await db_session.flush()

        result = await user_repository.get_by_telegram_id_with_exercises(333)

        assert result is not None
        assert result.current_category is not None
        assert result.current_category.name == "Math"

    async def test_null_current_category(self, user_repository, user_factory):
        await user_factory(telegram_id=444)

        result = await user_repository.get_by_telegram_id_with_exercises(444)

        assert result is not None
        assert result.current_category is None


class TestGetByIdWithExercises:
    async def test_returns_user(self, user_repository, user_factory):
        user = await user_factory(telegram_id=555)

        result = await user_repository.get_by_id_with_exercises(user.id)

        assert result is not None
        assert result.telegram_id == 555

    async def test_nonexistent_id(self, user_repository):
        result = await user_repository.get_by_id_with_exercises(999_999)
        assert result is None

    async def test_loads_exercises_and_category(
        self, user_repository, user_factory, category_factory, db_session,
    ):
        category = await category_factory(name="Physics")
        user = await user_factory(telegram_id=666)
        user.current_category_id = category.id
        await db_session.flush()

        result = await user_repository.get_by_id_with_exercises(user.id)

        assert result is not None
        assert result.current_category is not None
        assert result.current_category.name == "Physics"
        assert result.current_exercises == []


class TestBaseUserMethods:
    async def test_get_by_id(self, user_repository, user_factory):
        user = await user_factory(telegram_id=777)

        result = await user_repository.get_by_id(user.id)

        assert result is not None
        assert result.telegram_id == 777

    async def test_get_by_id_nonexistent(self, user_repository):
        result = await user_repository.get_by_id(999_999)
        assert result is None
