from datetime import UTC, datetime

from app.enums import HandlerType
from app.rendering.rich_renderer import RichRenderer
from app.schemas import CategoryDTO, ExerciseDTO, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

_CONTENT = {
    "text": "В результате <b><u>выходит</u></b>, что эти знания слишком поверхностны.",
    "word_with_definition": "<b>ВЫХОДИТЬ</b>. Быть обращённым куда-либо. <i>Окна выходят в сад.</i>",
}
_EXPL = "«появляться как следствие какого-либо процесса»"


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


class TestTask2View:
    async def test_create_task_builds_view(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(name="T2", handler_type=HandlerType.TASK_2_DRILL)
        await exercise_factory(category_id=cat.id, content=_CONTENT, answer="false", explanation=_EXPL)
        user = await user_factory()
        processor = processor_factory.get_processor(HandlerType.TASK_2_DRILL)
        resp = await processor.create_task(_user_cat(user, cat))
        assert resp.task_ui.view is not None
        assert resp.task_ui.options is not None
        out = RichRenderer().render_task(resp.task_ui.view)
        assert out.startswith("### Задание 2\n\n")
        # HTML контента не экранируется — отдаём как есть
        assert "> В результате <b><u>выходит</u></b>" in out
        assert "<b>ВЫХОДИТЬ</b>" in out

    async def test_process_answer_false_shows_meaning(
        self, processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="T2", handler_type=HandlerType.TASK_2_DRILL)
        ex = await exercise_factory(category_id=cat.id, content=_CONTENT, answer="false", explanation=_EXPL)
        user = await user_factory()
        processor = processor_factory.get_processor(HandlerType.TASK_2_DRILL)
        result = await processor.process_answer(_user_ex(user, cat, [ex]), "false")
        assert result.is_correct is True
        assert result.result_view is not None
        out = RichRenderer().render_result(result.result_view)
        assert out.startswith("**✅ Верно**\n\n**Ответ:** Не подходит")
        assert f"**Верное значение:** {_EXPL}" in out
        assert "<details><summary>Фрагмент текста</summary>" in out
        assert "<details><summary>Значение из задания</summary>" in out

    async def test_process_answer_true_no_meaning(
        self, processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="T2", handler_type=HandlerType.TASK_2_DRILL)
        ex = await exercise_factory(category_id=cat.id, content=_CONTENT, answer="true", explanation="")
        user = await user_factory()
        processor = processor_factory.get_processor(HandlerType.TASK_2_DRILL)
        result = await processor.process_answer(_user_ex(user, cat, [ex]), "false")
        assert result.is_correct is False
        out = RichRenderer().render_result(result.result_view)
        assert out.startswith("**❌ Неверно**\n\n**Правильный ответ:** Подходит")
        assert "Верное значение" not in out
