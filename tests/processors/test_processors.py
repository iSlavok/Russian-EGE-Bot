from datetime import UTC, datetime

import pytest

from app.enums import HandlerType
from app.processors.tasks.generic import SkipProcessor, SoonProcessor
from app.processors.tasks.task_01 import Task1DrillProcessor
from app.processors.tasks.task_02 import Task2DrillProcessor
from app.processors.tasks.task_03 import Task3ExamProcessor
from app.processors.tasks.task_06 import Task6ExamProcessor
from app.processors.tasks.task_17_20 import Task17ExamProcessor, Task18ExamProcessor, Task19ExamProcessor, Task20ExamProcessor
from app.processors.tasks.task_23_24 import Task23ExamProcessor, Task24ExamProcessor
from app.processors.tasks.task_25 import Task25ExamProcessor
from app.processors.tasks.task_26 import Task26ExamProcessor
from app.schemas import CategoryDTO, CheckResult, ExerciseDTO, TaskResponse, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_dto(user_orm, cat_orm):
    cat_dto = CategoryDTO(
        id=cat_orm.id, name=cat_orm.name,
        handler_type=cat_orm.handler_type, parent_id=cat_orm.parent_id,
    )
    return UserWithCategoryDTO(
        id=user_orm.id, telegram_id=user_orm.telegram_id,
        username=user_orm.username, full_name=user_orm.full_name,
        exercise_started_at=None, current_category=cat_dto,
    )


def _user_with_exercises_dto(user_orm, cat_orm, exercise_orms):
    cat_dto = CategoryDTO(
        id=cat_orm.id, name=cat_orm.name,
        handler_type=cat_orm.handler_type, parent_id=cat_orm.parent_id,
    )
    exercises = [
        ExerciseDTO(
            id=ex.id, category_id=ex.category_id, group_id=ex.group_id,
            order_index=ex.order_index, content=ex.content, answer=ex.answer,
            explanation=ex.explanation or "Объяснение", is_active=ex.is_active,
        )
        for ex in exercise_orms
    ]
    return UserWithExercisesDTO(
        id=user_orm.id, telegram_id=user_orm.telegram_id,
        username=user_orm.username, full_name=user_orm.full_name,
        exercise_started_at=datetime.now(UTC),
        current_category=cat_dto,
        current_category_id=cat_orm.id,
        current_exercises=exercises,
    )


# ===================================================================
# Generic processors (Skip, Soon) — parametrized
# ===================================================================

@pytest.mark.parametrize("processor_cls", [SkipProcessor, SoonProcessor])
class TestGenericProcessors:
    async def test_create_task(self, processor_cls, exercise_repository, user_answer_repository, exercise_selector,
                               user_factory, category_factory):
        processor = processor_cls(exercise_repository, user_answer_repository, exercise_selector)
        user = await user_factory()
        cat = await category_factory()
        dto = _user_dto(user, cat)
        result = await processor.create_task(dto)
        assert isinstance(result, TaskResponse)
        assert result.task_ui.view is not None

    async def test_process_answer(self, processor_cls, exercise_repository, user_answer_repository, exercise_selector,
                                  user_factory, category_factory):
        processor = processor_cls(exercise_repository, user_answer_repository, exercise_selector)
        user = await user_factory()
        cat = await category_factory()
        dto = _user_with_exercises_dto(user, cat, [])
        result = await processor.process_answer(dto, "anything")
        assert isinstance(result, CheckResult)
        assert result.is_correct is True


# ===================================================================
# Single-exercise processors with direct category — parametrized create_task
# ===================================================================

DIRECT_CATEGORY_CASES = [
    pytest.param(
        HandlerType.TASK_1_DRILL,
        {"text": "Текст задания", "instruction": "Выберите ответ"},
        "ответ",
        id="task1_drill",
    ),
    pytest.param(
        HandlerType.TASK_3_EXAM,
        {"text": "Фрагмент текста", "statements": ["Утв1", "Утв2", "Утв3", "Утв4", "Утв5"]},
        "135",
        id="task3_exam",
    ),
    pytest.param(
        HandlerType.TASK_17_EXAM,
        {"sentence": "Слово(1) текст(2) фраза", "correct_sentence": "Слово, текст, фраза"},
        "12",
        id="task17_exam",
    ),
    pytest.param(
        HandlerType.TASK_18_EXAM,
        {"sentence": "Слово(1) текст(2) фраза", "correct_sentence": "Слово, текст, фраза"},
        "12",
        id="task18_exam",
    ),
    pytest.param(
        HandlerType.TASK_19_EXAM,
        {"sentence": "Слово(1) текст(2) фраза", "correct_sentence": "Слово, текст, фраза"},
        "12",
        id="task19_exam",
    ),
    pytest.param(
        HandlerType.TASK_20_EXAM,
        {"sentence": "Слово(1) текст(2) фраза", "correct_sentence": "Слово, текст, фраза"},
        "12",
        id="task20_exam",
    ),
    pytest.param(
        HandlerType.TASK_25_EXAM,
        {"task": "Выпишите фразеологизм из предложений 1-3.", "sentences": "(1)Текст предложения."},
        "фразеологизм",
        id="task25_exam",
    ),
    pytest.param(
        HandlerType.TASK_26_EXAM,
        {"task": "Укажите средства связи предложений 1-3.", "sentences": "(1)Текст предложения."},
        "12",
        id="task26_exam",
    ),
    pytest.param(
        HandlerType.TASK_14_DRILL,
        {"sentence": "(ЧТО)БЫ пришли все вовремя"},
        "TOGETHER",
        id="task14_drill",
    ),
    pytest.param(
        HandlerType.TASK_15_DRILL,
        {"sentence": "Серебря{n}ый кубок стоял на полке", "word": "серебря{n}ый"},
        "н",
        id="task15_drill",
    ),
    pytest.param(
        HandlerType.TASK_21_EXAM,
        {"full_text": "(1)Подлежащее — сказуемое. (2)Тире — знак.", "task_type": "DASH", "answer_rule": "SUBJ_PRED"},
        "12",
        id="task21_exam",
    ),
    pytest.param(
        HandlerType.TASK_6_EXAM,
        {
            "sentence": "Предложение с ошибкой",
            "task_type": "REMOVE",
            "sentence_with_markup": "Предложение с <u>ошибкой</u>",
            "corrected_sentence": "Предложение с исправлением",
        },
        "ошибкой",
        id="task6_exam",
    ),
    pytest.param(
        HandlerType.TASK_2_DRILL,
        {"text": "Предложение с <b>выделенным</b> словом.", "word_with_definition": "Слово — значение"},
        "false",
        id="task2_drill",
    ),
]


@pytest.mark.parametrize("handler_type,content,answer", DIRECT_CATEGORY_CASES)
class TestDirectCategoryCreateTask:
    async def test_create_task_returns_response(
        self, handler_type, content, answer,
        processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="Cat", handler_type=handler_type)
        await exercise_factory(category_id=cat.id, content=content, answer=answer, explanation="Объяснение")
        user = await user_factory()
        dto = _user_dto(user, cat)

        processor = processor_factory.get_processor(handler_type)
        result = await processor.create_task(dto)
        assert isinstance(result, TaskResponse)
        assert result.task_ui.view is not None


@pytest.mark.parametrize("handler_type,content,answer", DIRECT_CATEGORY_CASES)
class TestDirectCategoryProcessAnswer:
    async def test_correct_answer(
        self, handler_type, content, answer,
        processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="Cat", handler_type=handler_type)
        ex = await exercise_factory(category_id=cat.id, content=content, answer=answer, explanation="Объяснение")
        user = await user_factory()
        dto = _user_with_exercises_dto(user, cat, [ex])

        processor = processor_factory.get_processor(handler_type)
        result = await processor.process_answer(dto, answer)
        assert isinstance(result, CheckResult)
        assert result.is_correct is True
        assert result.result_view is not None

    async def test_wrong_answer(
        self, handler_type, content, answer,
        processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="Cat", handler_type=handler_type)
        ex = await exercise_factory(category_id=cat.id, content=content, answer=answer, explanation="Объяснение")
        user = await user_factory()
        dto = _user_with_exercises_dto(user, cat, [ex])

        processor = processor_factory.get_processor(handler_type)
        result = await processor.process_answer(dto, "заведомо_неправильный_ответ_999")
        assert isinstance(result, CheckResult)
        assert result.is_correct is False


# ===================================================================
# Parent-category processors — parametrized
# ===================================================================

PARENT_CATEGORY_CASES = [
    pytest.param(
        HandlerType.TASK_8_DRILL,
        {"sentence": "Предложение с ошибкой", "corrected_sentence": "Исправленное предложение"},
        "participial_clause_error",
        id="task8_drill",
    ),
    pytest.param(
        HandlerType.TASK_9_DRILL,
        {"word": "пр{letter}морский", "incorrect_letter": "е"},
        "и",
        id="task9_drill",
    ),
    pytest.param(
        HandlerType.TASK_10_DRILL,
        {"word": "пр{letter}морский", "incorrect_letter": "е"},
        "и",
        id="task10_drill",
    ),
    pytest.param(
        HandlerType.TASK_11_DRILL,
        {"word": "приш{letter}л", "incorrect_letter": "о"},
        "ё",
        id="task11_drill",
    ),
    pytest.param(
        HandlerType.TASK_12_DRILL,
        {"word": "приш{letter}л", "incorrect_letter": "о"},
        "ё",
        id="task12_drill",
    ),
    pytest.param(
        HandlerType.TASK_13_DRILL,
        {"sentence": "(НЕ)видимые следы", "particle": "НЕ"},
        "SEPARATE",
        id="task13_drill",
    ),
    pytest.param(
        HandlerType.TASK_16_DRILL,
        {"sentence": "Солнце светило и птицы пели", "corrected_sentence": "Солнце светило, и птицы пели"},
        "1",
        id="task16_drill",
    ),
]


@pytest.mark.parametrize("handler_type,content,answer", PARENT_CATEGORY_CASES)
class TestParentCategoryCreateTask:
    async def test_create_task_returns_response(
        self, handler_type, content, answer,
        processor_factory, user_factory, category_factory, exercise_factory,
    ):
        parent = await category_factory(name="Parent", handler_type=handler_type)
        child = await category_factory(name="Child", handler_type=handler_type, parent_id=parent.id)
        await exercise_factory(category_id=parent.id, content=content, answer=answer, explanation="Объяснение")
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(handler_type)
        result = await processor.create_task(dto)
        assert isinstance(result, TaskResponse)
        assert result.task_ui.view is not None


@pytest.mark.parametrize("handler_type,content,answer", PARENT_CATEGORY_CASES)
class TestParentCategoryProcessAnswer:
    async def test_correct_answer(
        self, handler_type, content, answer,
        processor_factory, user_factory, category_factory, exercise_factory,
    ):
        parent = await category_factory(name="Parent", handler_type=handler_type)
        child = await category_factory(name="Child", handler_type=handler_type, parent_id=parent.id)
        ex = await exercise_factory(category_id=parent.id, content=content, answer=answer, explanation="Объяснение")
        user = await user_factory()
        dto = _user_with_exercises_dto(user, child, [ex])

        processor = processor_factory.get_processor(handler_type)
        result = await processor.process_answer(dto, answer)
        assert isinstance(result, CheckResult)
        assert result.is_correct is True

    async def test_wrong_answer(
        self, handler_type, content, answer,
        processor_factory, user_factory, category_factory, exercise_factory,
    ):
        parent = await category_factory(name="Parent", handler_type=handler_type)
        child = await category_factory(name="Child", handler_type=handler_type, parent_id=parent.id)
        ex = await exercise_factory(category_id=parent.id, content=content, answer=answer, explanation="Объяснение")
        user = await user_factory()
        dto = _user_with_exercises_dto(user, child, [ex])

        processor = processor_factory.get_processor(handler_type)
        result = await processor.process_answer(dto, "неправильный_ответ_999")
        assert isinstance(result, CheckResult)
        assert result.is_correct is False


# ===================================================================
# Task23/24 — create_task + process_answer
# ===================================================================

@pytest.mark.parametrize("handler_type", [HandlerType.TASK_23_EXAM, HandlerType.TASK_24_EXAM])
class TestTask2324Processors:
    async def test_create_task(
        self, handler_type,
        processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="Cat", handler_type=handler_type)
        await exercise_factory(
            category_id=cat.id,
            content={"text": "(1)Текст. (2)Ещё текст.", "options": ["Opt1", "Opt2", "Opt3", "Opt4", "Opt5"]},
            answer="135",
            explanation="Объяснение",
        )
        user = await user_factory()
        dto = _user_dto(user, cat)

        processor = processor_factory.get_processor(handler_type)
        result = await processor.create_task(dto)
        assert isinstance(result, TaskResponse)
        assert result.task_config is not None

    async def test_process_answer_correct(
        self, handler_type,
        processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="Cat", handler_type=handler_type)
        ex = await exercise_factory(
            category_id=cat.id,
            content={"text": "(1)Текст.", "options": ["O1", "O2", "O3", "O4", "O5"]},
            answer="13",
            explanation="Объяснение",
        )
        user = await user_factory()
        # ask_incorrect=False → correct answer is "13"
        dto = _user_with_exercises_dto(user, cat, [ex])
        dto.current_task_config = {"correct_digits": "13", "ask_incorrect": False}

        processor = processor_factory.get_processor(handler_type)
        result = await processor.process_answer(dto, "13")
        assert result.is_correct is True

    async def test_process_answer_incorrect(
        self, handler_type,
        processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="Cat", handler_type=handler_type)
        ex = await exercise_factory(
            category_id=cat.id,
            content={"text": "(1)Текст.", "options": ["O1", "O2", "O3", "O4", "O5"]},
            answer="13",
            explanation="Объяснение",
        )
        user = await user_factory()
        dto = _user_with_exercises_dto(user, cat, [ex])
        dto.current_task_config = {"correct_digits": "13", "ask_incorrect": False}

        processor = processor_factory.get_processor(handler_type)
        result = await processor.process_answer(dto, "245")
        assert result.is_correct is False


# ===================================================================
# Task21 Drill — single exercise
# ===================================================================

class TestTask21DrillProcessor:
    async def test_create_task(
        self, processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="Cat", handler_type=HandlerType.TASK_21_DRILL)
        await exercise_factory(
            category_id=cat.id,
            content={"text": "Предложение с тире — здесь.", "task_type": "DASH"},
            answer="SUBJ_PRED",
            explanation="Объяснение",
        )
        user = await user_factory()
        dto = _user_dto(user, cat)

        processor = processor_factory.get_processor(HandlerType.TASK_21_DRILL)
        result = await processor.create_task(dto)
        assert isinstance(result, TaskResponse)

    async def test_process_answer_correct(
        self, processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="Cat21c", handler_type=HandlerType.TASK_21_DRILL)
        ex = await exercise_factory(
            category_id=cat.id,
            content={"text": "Предложение с тире — здесь.", "task_type": "DASH"},
            answer="SUBJ_PRED",
            explanation="Объяснение",
        )
        user = await user_factory()
        dto = _user_with_exercises_dto(user, cat, [ex])

        processor = processor_factory.get_processor(HandlerType.TASK_21_DRILL)
        result = await processor.process_answer(dto, "SUBJ_PRED")
        assert result.is_correct is True

    async def test_process_answer_wrong(
        self, processor_factory, user_factory, category_factory, exercise_factory,
    ):
        cat = await category_factory(name="Cat21w", handler_type=HandlerType.TASK_21_DRILL)
        ex = await exercise_factory(
            category_id=cat.id,
            content={"text": "Предложение с тире — здесь.", "task_type": "DASH"},
            answer="SUBJ_PRED",
            explanation="Объяснение",
        )
        user = await user_factory()
        dto = _user_with_exercises_dto(user, cat, [ex])

        processor = processor_factory.get_processor(HandlerType.TASK_21_DRILL)
        result = await processor.process_answer(dto, "BSP")
        assert result.is_correct is False


# ===================================================================
# base_processor helpers
# ===================================================================

class TestBaseProcessorHelpers:
    async def test_require_category_raises(self, processor_factory):
        from app.exceptions import NoCategoryError
        processor = processor_factory.get_processor(HandlerType.TASK_1_DRILL)
        user = UserWithCategoryDTO(
            id=1, telegram_id=1, username=None, full_name="U",
            exercise_started_at=None, current_category=None,
        )
        with pytest.raises(NoCategoryError):
            processor._require_category(user)

    async def test_require_parent_raises(self, processor_factory, category_factory):
        from app.exceptions import InvalidCategoryStructureError
        processor = processor_factory.get_processor(HandlerType.TASK_2_DRILL)
        cat = await category_factory(name="No parent")
        dto = _user_dto(object.__new__(type("U", (), {"id": 1, "telegram_id": 1, "username": None, "full_name": "U"})), cat)
        # Use a proper DTO with no parent
        cat_dto = CategoryDTO(id=cat.id, name="No parent", handler_type=None, parent_id=None)
        user = UserWithCategoryDTO(
            id=1, telegram_id=1, username=None, full_name="U",
            exercise_started_at=None, current_category=cat_dto,
        )
        with pytest.raises(InvalidCategoryStructureError):
            processor._require_parent_category_id(user)

    async def test_fetch_exercise_empty_raises(self, processor_factory, category_factory, user_factory):
        from app.exceptions import TaskForUserNotFoundError
        processor = processor_factory.get_processor(HandlerType.TASK_1_DRILL)
        cat = await category_factory(name="Empty")
        user = await user_factory()
        with pytest.raises(TaskForUserNotFoundError):
            await processor._fetch_exercise(cat.id, user.id)

    async def test_fetch_exercises_not_enough_raises(
        self, processor_factory, category_factory, exercise_factory, user_factory,
    ):
        from app.exceptions import TaskForUserNotFoundError
        processor = processor_factory.get_processor(HandlerType.TASK_1_DRILL)
        cat = await category_factory()
        await exercise_factory(category_id=cat.id)
        user = await user_factory()
        with pytest.raises(TaskForUserNotFoundError):
            await processor._fetch_exercises(cat.id, user.id, count=5)

    async def test_compute_solve_time(self, processor_factory, user_factory, category_factory):
        processor = processor_factory.get_processor(HandlerType.TASK_1_DRILL)
        user = await user_factory()
        cat = await category_factory()
        dto = _user_with_exercises_dto(user, cat, [])
        dto.exercise_started_at = datetime.now(UTC)
        t = processor._compute_solve_time(dto)
        assert t >= 0

    async def test_compute_solve_time_none(self, processor_factory, user_factory, category_factory):
        processor = processor_factory.get_processor(HandlerType.TASK_1_DRILL)
        user = await user_factory()
        cat = await category_factory()
        dto = _user_with_exercises_dto(user, cat, [])
        dto.exercise_started_at = None
        t = processor._compute_solve_time(dto)
        assert t == 0

    async def test_process_answer_single_exercise_no_exercises_raises(self, processor_factory):
        from app.exceptions import NoCurrentExercisesError
        processor = processor_factory.get_processor(HandlerType.TASK_2_DRILL)
        dto = UserWithExercisesDTO(
            id=1, telegram_id=1, username=None, full_name="U",
            exercise_started_at=None, current_category=None,
            current_exercises=None,
        )
        with pytest.raises(NoCurrentExercisesError):
            await processor._process_answer_single_exercise(dto, "answer")

    async def test_get_ordered_exercises(self, processor_factory, user_factory, category_factory, exercise_factory):
        processor = processor_factory.get_processor(HandlerType.TASK_1_DRILL)
        cat = await category_factory()
        ex1 = await exercise_factory(category_id=cat.id, answer="a")
        ex2 = await exercise_factory(category_id=cat.id, answer="b")
        ex3 = await exercise_factory(category_id=cat.id, answer="c")
        user = await user_factory()
        dto = _user_with_exercises_dto(user, cat, [ex1, ex2, ex3])

        ordered = processor._get_ordered_exercises(dto, [ex3.id, ex1.id, ex2.id])
        assert [e.id for e in ordered] == [ex3.id, ex1.id, ex2.id]
