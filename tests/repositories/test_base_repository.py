import pytest


class TestGetManyFromCache:
    async def test_returns_cached_objects(self, category_repository, category_factory):
        cat1 = await category_factory(name="Cached 1")
        cat2 = await category_factory(name="Cached 2")
        # загрузим в identity_map через get_by_id
        await category_repository.get_by_id(cat1.id)
        await category_repository.get_by_id(cat2.id)

        result = category_repository.get_many_from_cache([cat1.id, cat2.id])
        assert len(result) == 2
        result_ids = {r.id for r in result}
        assert result_ids == {cat1.id, cat2.id}

    async def test_skips_missing_ids(self, category_repository, category_factory):
        cat = await category_factory(name="Only one")
        await category_repository.get_by_id(cat.id)

        result = category_repository.get_many_from_cache([cat.id, 999_999])
        assert len(result) == 1
        assert result[0].id == cat.id

    async def test_empty_ids(self, category_repository):
        result = category_repository.get_many_from_cache([])
        assert result == []

    async def test_none_in_cache(self, category_repository):
        result = category_repository.get_many_from_cache([999_999])
        assert result == []


class TestRefresh:
    async def test_refresh_reloads_object(self, category_repository, category_factory, db_session):
        cat = await category_factory(name="Before")
        from sqlalchemy import update
        from app.models import Category
        await db_session.execute(
            update(Category).where(Category.id == cat.id).values(name="After")
        )
        # expire сбрасывает кэш атрибутов, но не перезагружает — следующее обращение
        # к атрибуту вызовет lazy load; refresh делает это явно одним запросом
        db_session.expire(cat)

        await category_repository.refresh(cat)
        assert cat.name == "After"


class TestCommit:
    async def test_commit_persists(self, category_repository, category_factory, db_session):
        cat = await category_factory(name="Committed")
        # flush уже произошёл в factory, commit зафиксирует транзакцию
        # в тестовом окружении (rollback_only) commit не упадёт, но метод вызовется
        await category_repository.commit()


class TestFlush:
    async def test_flush_single_object(self, category_repository, db_session):
        from app.models import Category
        cat = Category(name="Flush single")
        category_repository.add(cat)
        assert cat.id is None
        await category_repository.flush(cat)
        assert cat.id is not None

    async def test_flush_none(self, category_repository):
        # flush(None) — flush всей сессии
        await category_repository.flush(None)

    async def test_flush_sequence(self, category_repository, db_session):
        from app.models import Category
        cat1 = Category(name="Flush seq 1")
        cat2 = Category(name="Flush seq 2")
        category_repository.add(cat1)
        category_repository.add(cat2)
        await category_repository.flush([cat1, cat2])
        assert cat1.id is not None
        assert cat2.id is not None


class TestGetByIds:
    async def test_returns_matching(self, category_repository, category_factory):
        cat1 = await category_factory(name="A")
        cat2 = await category_factory(name="B")
        await category_factory(name="C")

        result = await category_repository.get_by_ids([cat1.id, cat2.id])
        result_ids = {r.id for r in result}
        assert result_ids == {cat1.id, cat2.id}

    async def test_empty_ids_returns_empty(self, category_repository):
        result = await category_repository.get_by_ids([])
        assert list(result) == []

    async def test_nonexistent_ids_skipped(self, category_repository, category_factory):
        cat = await category_factory(name="Exists")
        result = await category_repository.get_by_ids([cat.id, 999_999])
        assert len(result) == 1
        assert result[0].id == cat.id
