from datetime import UTC, datetime

from app.enums import HandlerType
from app.rendering.rich_renderer import render_result, render_task
from app.schemas import CategoryDTO, ExerciseDTO, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

_CONTENT = {"instruction": "Подберите вводное слово.", "text": "Штампов < . . . > моделей."}
_EXPL = "<i>Штампов </i><b>в частности</b><i> моделей.</i>"


def _cat_dto(cat):
    return CategoryDTO(id=cat.id, name=cat.name, handler_type=cat.handler_type, parent_id=cat.parent_id)


def _user_cat(user, cat):
    return UserWithCategoryDTO(
        id=user.id, telegram_id=user.telegram_id, username=user.username,
        full_name=user.full_name, exercise_started_at=None, current_category=_cat_dto(cat),
    )


def _user_ex(user, cat, exercises):
    dtos = [ExerciseDTO(
        id=e.id, category_id=e.category_id, group_id=e.group_id, order_index=e.order_index,
        content=e.content, answer=e.answer, explanation=e.explanation, is_active=e.is_active,
    ) for e in exercises]
    return UserWithExercisesDTO(
        id=user.id, telegram_id=user.telegram_id, username=user.username, full_name=user.full_name,
        exercise_started_at=datetime.now(UTC), current_category=_cat_dto(cat),
        current_category_id=cat.id, current_exercises=dtos, current_task_config=None,
    )


class TestTask1View:
    async def test_create_task_builds_view(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(name="T1", handler_type=HandlerType.TASK_1_DRILL)
        await exercise_factory(category_id=cat.id, content=_CONTENT, answer="в частности;например", explanation=_EXPL)
        user = await user_factory()
        processor = processor_factory.get_processor(HandlerType.TASK_1_DRILL)
        resp = await processor.create_task(_user_cat(user, cat))
        assert resp.task_ui.view is not None
        out = render_task(resp.task_ui.view)
        assert out.startswith("### Задание 1\n\nПодберите вводное слово.\n\n---\n\n> ")
        assert "&lt; . . . &gt;" in out

    async def test_process_answer_correct_underlines_user(
        self, processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="T1", handler_type=HandlerType.TASK_1_DRILL)
        ex = await exercise_factory(category_id=cat.id, content=_CONTENT, answer="в частности;например", explanation=_EXPL)
        user = await user_factory()
        processor = processor_factory.get_processor(HandlerType.TASK_1_DRILL)
        result = await processor.process_answer(_user_ex(user, cat, [ex]), "например")
        assert result.is_correct is True
        assert result.result_view is not None
        out = render_result(result.result_view)
        assert out.startswith("**✅ Верно**")
        assert "<u>например</u>" in out
        assert "<details><summary>Фрагмент текста</summary>" in out
        assert "<u><b>например</b></u>" in out

    async def test_process_answer_wrong_opens_fragment(
        self, processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="T1", handler_type=HandlerType.TASK_1_DRILL)
        ex = await exercise_factory(category_id=cat.id, content=_CONTENT, answer="в частности", explanation=_EXPL)
        user = await user_factory()
        processor = processor_factory.get_processor(HandlerType.TASK_1_DRILL)
        result = await processor.process_answer(_user_ex(user, cat, [ex]), "поэтому")
        assert result.is_correct is False
        out = render_result(result.result_view)
        assert out.startswith("**❌ Неверно**\n\n**Ваш ответ:** ~~поэтому~~")
        assert "<details open><summary>Фрагмент текста</summary>" in out
        assert "<u><b>в частности</b></u>" in out
