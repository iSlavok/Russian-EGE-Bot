import pytest
from sqlalchemy import insert

from app.enums import HandlerType
from app.models.user_model import user_current_exercises
from app.schemas.category_schemas import CategoryDTO, CategoryWithChildrenDTO
from app.schemas.exercise_schemas import ExerciseDTO
from app.schemas.user_schemas import UserDTO, UserWithCategoryDTO, UserWithExercisesDTO


class TestCategoryDTO:
    async def test_from_orm_obj(self, category_factory):
        cat = await category_factory(name="Задание 1", handler_type=HandlerType.TASK_1_DRILL)
        dto = CategoryDTO.from_orm_obj(cat)
        assert dto.id == cat.id
        assert dto.name == "Задание 1"
        assert dto.handler_type == HandlerType.TASK_1_DRILL
        assert dto.parent_id is None

    async def test_from_orm_obj_with_parent(self, category_factory):
        parent = await category_factory(name="Родитель")
        child = await category_factory(name="Дочерний", parent_id=parent.id)
        dto = CategoryDTO.from_orm_obj(child)
        assert dto.parent_id == parent.id

    async def test_from_orm_obj_no_handler_type(self, category_factory):
        cat = await category_factory(name="Без handler")
        dto = CategoryDTO.from_orm_obj(cat)
        assert dto.handler_type is None


class TestCategoryWithChildrenDTO:
    async def test_from_orm_obj_with_children(self, category_factory, category_repository):
        parent = await category_factory(name="Родитель")
        await category_factory(name="Ребёнок 1", parent_id=parent.id)
        await category_factory(name="Ребёнок 2", parent_id=parent.id)

        loaded = await category_repository.get_by_id_with_children(parent.id)
        dto = CategoryWithChildrenDTO.from_orm_obj(loaded)
        assert dto.name == "Родитель"
        assert len(dto.children) == 2
        assert all(isinstance(c, CategoryDTO) for c in dto.children)

    async def test_from_orm_obj_no_children(self, category_factory, category_repository):
        cat = await category_factory(name="Одинокий")
        loaded = await category_repository.get_by_id_with_children(cat.id)
        dto = CategoryWithChildrenDTO.from_orm_obj(loaded)
        assert dto.children == []


class TestExerciseDTO:
    async def test_from_orm_obj(self, category_factory, exercise_factory):
        cat = await category_factory()
        ex = await exercise_factory(
            category_id=cat.id,
            content={"text": "Вопрос"},
            answer="ответ",
            explanation="Потому что",
        )
        dto = ExerciseDTO.from_orm_obj(ex)
        assert dto.id == ex.id
        assert dto.category_id == cat.id
        assert dto.content == {"text": "Вопрос"}
        assert dto.answer == "ответ"
        assert dto.explanation == "Потому что"
        assert dto.is_active is True
        assert dto.group_id is None
        assert dto.order_index is None

    async def test_from_orm_obj_with_group(self, category_factory, exercise_factory):
        cat = await category_factory()
        gid = "11111111-1111-1111-1111-111111111111"
        ex = await exercise_factory(category_id=cat.id, group_id=gid, order_index=3)
        dto = ExerciseDTO.from_orm_obj(ex)
        assert str(dto.group_id) == gid
        assert dto.order_index == 3


class TestUserDTO:
    async def test_from_orm_obj(self, user_factory):
        user = await user_factory(telegram_id=999, username="ivan", full_name="Иван Иванов")
        dto = UserDTO.from_orm_obj(user)
        assert dto.id == user.id
        assert dto.telegram_id == 999
        assert dto.username == "ivan"
        assert dto.full_name == "Иван Иванов"
        assert dto.exercise_started_at is None
        assert dto.current_task_config is None
        assert dto.current_category_id is None


class TestUserWithCategoryDTO:
    async def test_from_orm_obj_with_category(self, user_factory, category_factory, user_repository, db_session):
        cat = await category_factory(name="Категория", handler_type=HandlerType.TASK_1_DRILL)
        user = await user_factory()
        user.current_category_id = cat.id
        await db_session.flush()

        loaded = await user_repository.get_by_id_with_exercises(user.id)
        dto = UserWithCategoryDTO.from_orm_obj(loaded, load_category=True)
        assert dto.current_category is not None
        assert dto.current_category.name == "Категория"

    async def test_from_orm_obj_no_category(self, user_factory):
        user = await user_factory()
        dto = UserWithCategoryDTO.from_orm_obj(user, load_category=True)
        assert dto.current_category is None

    async def test_from_orm_obj_load_category_false(self, user_factory, category_factory, user_repository, db_session):
        cat = await category_factory(name="Категория")
        user = await user_factory()
        user.current_category_id = cat.id
        await db_session.flush()

        loaded = await user_repository.get_by_id_with_exercises(user.id)
        dto = UserWithCategoryDTO.from_orm_obj(loaded, load_category=False)
        assert dto.current_category is None


class TestUserWithExercisesDTO:
    async def _link_exercises(self, db_session, user_id, exercise_ids):
        for eid in exercise_ids:
            await db_session.execute(
                insert(user_current_exercises).values(user_id=user_id, exercise_id=eid)
            )
        await db_session.flush()

    async def test_from_orm_obj_with_exercises(
        self, user_factory, category_factory, exercise_factory, user_repository, db_session,
    ):
        cat = await category_factory()
        ex1 = await exercise_factory(category_id=cat.id, answer="1")
        ex2 = await exercise_factory(category_id=cat.id, answer="2")
        user = await user_factory()
        user.current_category_id = cat.id
        await db_session.flush()
        await self._link_exercises(db_session, user.id, [ex1.id, ex2.id])

        loaded = await user_repository.get_by_id_with_exercises(user.id)
        dto = UserWithExercisesDTO.from_orm_obj(loaded)
        assert dto.current_exercises is not None
        assert len(dto.current_exercises) == 2
        assert all(isinstance(e, ExerciseDTO) for e in dto.current_exercises)

    async def test_from_orm_obj_no_exercises(self, user_factory, user_repository):
        user = await user_factory()
        loaded = await user_repository.get_by_id_with_exercises(user.id)
        dto = UserWithExercisesDTO.from_orm_obj(loaded)
        assert dto.current_exercises is None

    async def test_from_orm_obj_load_exercises_false(
        self, user_factory, category_factory, exercise_factory, user_repository, db_session,
    ):
        cat = await category_factory()
        ex = await exercise_factory(category_id=cat.id)
        user = await user_factory()
        await db_session.flush()
        await self._link_exercises(db_session, user.id, [ex.id])

        loaded = await user_repository.get_by_id_with_exercises(user.id)
        dto = UserWithExercisesDTO.from_orm_obj(loaded, load_exercises=False)
        assert dto.current_exercises is None

    async def test_from_orm_obj_load_both_false(self, user_factory, category_factory, user_repository, db_session):
        cat = await category_factory(name="Cat")
        user = await user_factory()
        user.current_category_id = cat.id
        await db_session.flush()

        loaded = await user_repository.get_by_id_with_exercises(user.id)
        dto = UserWithExercisesDTO.from_orm_obj(loaded, load_exercises=False, load_category=False)
        assert dto.current_category is None
        assert dto.current_exercises is None
