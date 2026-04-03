import pytest


class TestGetRoots:
    async def test_empty_db(self, category_repository):
        roots = await category_repository.get_roots()
        assert list(roots) == []

    async def test_returns_only_root_categories(self, category_repository, category_factory):
        root1 = await category_factory(name="Root 1")
        root2 = await category_factory(name="Root 2")
        await category_factory(name="Child", parent_id=root1.id)

        roots = await category_repository.get_roots()

        root_ids = [r.id for r in roots]
        assert root1.id in root_ids
        assert root2.id in root_ids
        assert len(root_ids) == 2

    async def test_ordered_by_id_asc(self, category_repository, category_factory):
        a = await category_factory(name="B-second")
        b = await category_factory(name="A-first")

        roots = await category_repository.get_roots()

        assert roots[0].id == a.id
        assert roots[1].id == b.id


class TestGetByIdWithChildren:
    async def test_returns_category_with_children(self, category_repository, category_factory):
        parent = await category_factory(name="Parent")
        child1 = await category_factory(name="Child 1", parent_id=parent.id)
        child2 = await category_factory(name="Child 2", parent_id=parent.id)

        result = await category_repository.get_by_id_with_children(parent.id)

        assert result is not None
        assert result.id == parent.id
        child_ids = {c.id for c in result.children}
        assert child_ids == {child1.id, child2.id}

    async def test_no_children(self, category_repository, category_factory):
        category = await category_factory(name="Lonely")

        result = await category_repository.get_by_id_with_children(category.id)

        assert result is not None
        assert result.children == []

    async def test_nonexistent_id(self, category_repository):
        result = await category_repository.get_by_id_with_children(999_999)
        assert result is None

    async def test_does_not_include_grandchildren(self, category_repository, category_factory):
        root = await category_factory(name="Root")
        child = await category_factory(name="Child", parent_id=root.id)
        await category_factory(name="Grandchild", parent_id=child.id)

        result = await category_repository.get_by_id_with_children(root.id)

        assert result is not None
        assert len(result.children) == 1
        assert result.children[0].id == child.id


class TestGetByIdWithTree:
    async def test_full_subtree(self, category_repository, category_factory):
        root = await category_factory(name="Root")
        child = await category_factory(name="Child", parent_id=root.id)
        grandchild = await category_factory(name="Grandchild", parent_id=child.id)

        tree = await category_repository.get_by_id_with_tree(root.id)

        tree_ids = {c.id for c in tree}
        assert tree_ids == {root.id, child.id, grandchild.id}

    async def test_single_node(self, category_repository, category_factory):
        node = await category_factory(name="Single")

        tree = await category_repository.get_by_id_with_tree(node.id)

        assert len(tree) == 1
        assert tree[0].id == node.id

    async def test_does_not_include_siblings(self, category_repository, category_factory):
        root = await category_factory(name="Root")
        child_a = await category_factory(name="A", parent_id=root.id)
        child_b = await category_factory(name="B", parent_id=root.id)
        await category_factory(name="A-child", parent_id=child_a.id)

        tree = await category_repository.get_by_id_with_tree(child_a.id)

        tree_ids = {c.id for c in tree}
        assert child_b.id not in tree_ids
        assert root.id not in tree_ids


class TestBaseRepositoryMethods:
    """Smoke-tests for inherited BaseRepository methods via CategoryRepository."""

    async def test_get_by_id(self, category_repository, category_factory):
        category = await category_factory(name="Findable")

        result = await category_repository.get_by_id(category.id)

        assert result is not None
        assert result.name == "Findable"

    async def test_get_by_id_nonexistent(self, category_repository):
        result = await category_repository.get_by_id(999_999)
        assert result is None

    async def test_add_and_flush(self, category_repository, db_session):
        from app.models import Category

        cat = Category(name="Added")
        category_repository.add(cat)
        await category_repository.flush(cat)

        result = await category_repository.get_by_id(cat.id)
        assert result is not None
        assert result.name == "Added"

    async def test_delete(self, category_repository, category_factory):
        cat = await category_factory(name="ToDelete")
        cat_id = cat.id

        await category_repository.delete(cat)
        await category_repository.flush()

        result = await category_repository.get_by_id(cat_id)
        assert result is None
