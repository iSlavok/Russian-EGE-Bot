import pytest

from app.exceptions import CategoryNotFoundError
from app.repositories import CategoryRepository
from app.services.category_service import CategoryService


@pytest.fixture
def category_service(db_session, category_repository):
    return CategoryService(session=db_session, category_repository=category_repository)


class TestGetRootCategories:
    async def test_returns_dtos(self, category_service, category_factory):
        await category_factory(name="Root 1")
        await category_factory(name="Root 2")

        result = await category_service.get_root_categories()
        assert len(result) == 2
        names = {c.name for c in result}
        assert names == {"Root 1", "Root 2"}

    async def test_empty(self, category_service):
        result = await category_service.get_root_categories()
        assert result == []

    async def test_excludes_children(self, category_service, category_factory):
        root = await category_factory(name="Root")
        await category_factory(name="Child", parent_id=root.id)

        result = await category_service.get_root_categories()
        assert len(result) == 1
        assert result[0].name == "Root"


class TestGetByIdWithChildren:
    async def test_happy_path(self, category_service, category_factory):
        parent = await category_factory(name="Parent")
        await category_factory(name="Child 1", parent_id=parent.id)
        await category_factory(name="Child 2", parent_id=parent.id)

        result = await category_service.get_by_id_with_children(parent.id)
        assert result.name == "Parent"
        assert len(result.children) == 2

    async def test_not_found(self, category_service):
        with pytest.raises(CategoryNotFoundError):
            await category_service.get_by_id_with_children(999_999)


class TestGetByIdWithTree:
    async def test_happy_path(self, category_service, category_factory):
        root = await category_factory(name="Root")
        child = await category_factory(name="Child", parent_id=root.id)
        await category_factory(name="Grandchild", parent_id=child.id)

        result = await category_service.get_by_id_with_tree(root.id)
        assert len(result) == 3
        names = {c.name for c in result}
        assert names == {"Root", "Child", "Grandchild"}

    async def test_not_found(self, category_service):
        with pytest.raises(CategoryNotFoundError):
            await category_service.get_by_id_with_tree(999_999)
