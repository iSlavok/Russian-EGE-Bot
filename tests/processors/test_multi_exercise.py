"""Tests for multi-exercise processors (Task4, Task5, Task7 etc.)."""
import uuid
from datetime import UTC, datetime

import pytest

from app.enums import HandlerType
from app.rendering.rich_renderer import RichRenderer
from app.schemas import CategoryDTO, ExerciseDTO, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO


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


def _user_with_exercises(user_orm, cat_orm, exercise_orms, task_config=None):
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
        current_task_config=task_config,
    )


# ===================================================================
# Task4 Drill — binary choice stress
# ===================================================================

class TestTask4DrillProcessor:
    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="Parent", handler_type=HandlerType.TASK_4_DRILL)
        child = await category_factory(name="Child", handler_type=HandlerType.TASK_4_DRILL, parent_id=parent.id)
        await exercise_factory(
            category_id=parent.id,
            content={"word": "банты", "incorrect_stress": 2},
            answer="1",
        )
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(HandlerType.TASK_4_DRILL)
        result = await processor.create_task(dto)
        assert result.task_ui.options is not None
        assert len(result.task_ui.options) == 2

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P", handler_type=HandlerType.TASK_4_DRILL)
        child = await category_factory(name="C", handler_type=HandlerType.TASK_4_DRILL, parent_id=parent.id)
        ex = await exercise_factory(
            category_id=parent.id,
            content={"word": "банты", "incorrect_stress": 2},
            answer="1",
        )
        user = await user_factory()
        dto = _user_with_exercises(user, child, [ex])

        processor = processor_factory.get_processor(HandlerType.TASK_4_DRILL)
        result = await processor.process_answer(dto, "1")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P", handler_type=HandlerType.TASK_4_DRILL)
        child = await category_factory(name="C", handler_type=HandlerType.TASK_4_DRILL, parent_id=parent.id)
        ex = await exercise_factory(
            category_id=parent.id,
            content={"word": "банты", "incorrect_stress": 2},
            answer="1",
        )
        user = await user_factory()
        dto = _user_with_exercises(user, child, [ex])

        processor = processor_factory.get_processor(HandlerType.TASK_4_DRILL)
        result = await processor.process_answer(dto, "2")
        assert result.is_correct is False


# ===================================================================
# Task4 Exam — 5 words, select correctly stressed
# ===================================================================

class TestTask4ExamProcessor:
    async def _setup(self, category_factory, exercise_factory):
        parent = await category_factory(name="P4", handler_type=HandlerType.TASK_4_EXAM)
        child = await category_factory(name="C4", handler_type=HandlerType.TASK_4_EXAM, parent_id=parent.id)
        exercises = []
        for i in range(5):
            ex = await exercise_factory(
                category_id=parent.id,
                content={"word": f"слово{i}", "incorrect_stress": 2},
                answer="1",
                explanation=f"Объяснение {i}",
            )
            exercises.append(ex)
        return parent, child, exercises

    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent, child, exercises = await self._setup(category_factory, exercise_factory)
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(HandlerType.TASK_4_EXAM)
        result = await processor.create_task(dto)
        assert result.task_config is not None
        assert len(result.exercise_ids) == 5

    async def test_process_answer(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent, child, exercises = await self._setup(category_factory, exercise_factory)
        user = await user_factory()

        exercise_ids = [ex.id for ex in exercises]
        # All shown with correct stress (position 1) → all are correct → answer "12345"
        stress_positions = [1, 1, 1, 1, 1]
        task_config = {"exercise_ids": exercise_ids, "stress_positions": stress_positions}

        dto = _user_with_exercises(user, child, exercises, task_config)
        processor = processor_factory.get_processor(HandlerType.TASK_4_EXAM)
        result = await processor.process_answer(dto, "12345")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent, child, exercises = await self._setup(category_factory, exercise_factory)
        user = await user_factory()

        exercise_ids = [ex.id for ex in exercises]
        # Only word 1 shown correctly (stress=1=answer), rest shown with incorrect (stress=2)
        stress_positions = [1, 2, 2, 2, 2]
        task_config = {"exercise_ids": exercise_ids, "stress_positions": stress_positions}

        dto = _user_with_exercises(user, child, exercises, task_config)
        processor = processor_factory.get_processor(HandlerType.TASK_4_EXAM)
        result = await processor.process_answer(dto, "12345")
        assert result.is_correct is False


# ===================================================================
# Task5 Drill — paronym selection
# ===================================================================

class TestTask5DrillProcessor:
    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P5", handler_type=HandlerType.TASK_5_DRILL)
        child = await category_factory(name="C5", handler_type=HandlerType.TASK_5_DRILL, parent_id=parent.id)
        await exercise_factory(
            category_id=parent.id,
            content={
                "sentence": "Он был {word} человеком.",
                "words": ["дипломатичный", "дипломатический"],
                "paronyms": [
                    {"explanation": "Тактичный", "inflected_form": "дипломатичным"},
                    {"explanation": "Относящийся к дипломатии", "inflected_form": "дипломатическим"},
                ],
                "secondary_number": 2,
            },
            answer="1",
            explanation="Объяснение",
        )
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(HandlerType.TASK_5_DRILL)
        result = await processor.create_task(dto)
        assert result.task_ui.options is not None
        assert len(result.task_ui.options) == 2

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P5", handler_type=HandlerType.TASK_5_DRILL)
        child = await category_factory(name="C5", handler_type=HandlerType.TASK_5_DRILL, parent_id=parent.id)
        ex = await exercise_factory(
            category_id=parent.id,
            content={
                "sentence": "Он был {word} человеком.",
                "words": ["дипломатичный", "дипломатический"],
                "paronyms": [
                    {"explanation": "Тактичный", "inflected_form": "дипломатичным"},
                    {"explanation": "Относящийся к дипломатии", "inflected_form": "дипломатическим"},
                ],
                "secondary_number": 2,
            },
            answer="1",
        )
        user = await user_factory()
        dto = _user_with_exercises(user, child, [ex])

        processor = processor_factory.get_processor(HandlerType.TASK_5_DRILL)
        result = await processor.process_answer(dto, "1")
        assert result.is_correct is True
        assert result.result_view is not None
        assert "дипломатичным" in RichRenderer().render_result(result.result_view).lower()


# ===================================================================
# Task7 Drill — phrase with grammar error
# ===================================================================

class TestTask7DrillProcessor:
    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P7", handler_type=HandlerType.TASK_7_DRILL)
        child = await category_factory(name="C7", handler_type=HandlerType.TASK_7_DRILL, parent_id=parent.id)
        await exercise_factory(
            category_id=parent.id,
            content={"phrase": "пара {word}", "incorrect_answer": "туфлей"},
            answer="туфель",
            explanation="Объяснение",
        )
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(HandlerType.TASK_7_DRILL)
        result = await processor.create_task(dto)
        assert result.task_ui.options is not None
        assert len(result.task_ui.options) == 2

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P7", handler_type=HandlerType.TASK_7_DRILL)
        child = await category_factory(name="C7", handler_type=HandlerType.TASK_7_DRILL, parent_id=parent.id)
        ex = await exercise_factory(
            category_id=parent.id,
            content={"phrase": "пара {word}", "incorrect_answer": "туфлей"},
            answer="туфель",
            explanation="Объяснение",
        )
        user = await user_factory()
        dto = _user_with_exercises(user, child, [ex])

        processor = processor_factory.get_processor(HandlerType.TASK_7_DRILL)
        result = await processor.process_answer(dto, "туфель")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P7", handler_type=HandlerType.TASK_7_DRILL)
        child = await category_factory(name="C7", handler_type=HandlerType.TASK_7_DRILL, parent_id=parent.id)
        ex = await exercise_factory(
            category_id=parent.id,
            content={"phrase": "пара {word}", "incorrect_answer": "туфлей"},
            answer="туфель",
            explanation="Объяснение",
        )
        user = await user_factory()
        dto = _user_with_exercises(user, child, [ex])

        processor = processor_factory.get_processor(HandlerType.TASK_7_DRILL)
        result = await processor.process_answer(dto, "туфлей")
        assert result.is_correct is False


# ===================================================================
# Task4 context_before/context_after
# ===================================================================

class TestTask4WithContext:
    async def test_create_task_with_context(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P4c", handler_type=HandlerType.TASK_4_DRILL)
        child = await category_factory(name="C4c", handler_type=HandlerType.TASK_4_DRILL, parent_id=parent.id)
        await exercise_factory(
            category_id=parent.id,
            content={"word": "банты", "incorrect_stress": 2, "context_before": "красивые", "context_after": "на столе"},
            answer="1",
        )
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(HandlerType.TASK_4_DRILL)
        result = await processor.create_task(dto)
        assert result.task_ui.view is not None
        out = RichRenderer().render_task(result.task_ui.view)
        assert "красивые" in out
        assert "на столе" in out


# ===================================================================
# Task5 Exam — process_answer
# ===================================================================

class TestTask5ExamProcessor:
    async def _make_exercises(self, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_5_EXAM)
        exercises = []
        for i in range(5):
            ex = await exercise_factory(
                category_id=cat.id,
                content={
                    "sentence": f"Он {{word}} предмет {i}.",
                    "words": [f"словоА{i}", f"словоБ{i}"],
                    "paronyms": [
                        {"explanation": f"Значение А{i}", "inflected_form": f"формаА{i}"},
                        {"explanation": f"Значение Б{i}", "inflected_form": f"формаБ{i}"},
                    ],
                    "secondary_number": 2,
                },
                answer="1",
                explanation=f"Объяснение {i}",
            )
            exercises.append(ex)
        return cat, exercises

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "wrong_sentence_index": 0}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_5_EXAM)
        result = await processor.process_answer(dto, "формаА0")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "wrong_sentence_index": 0}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_5_EXAM)
        result = await processor.process_answer(dto, "неправильно")
        assert result.is_correct is False


# ===================================================================
# Task7 Exam — process_answer
# ===================================================================

class TestTask7ExamProcessor:
    async def _make_exercises(self, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_7_EXAM)
        exercises = []
        for i in range(5):
            ex = await exercise_factory(
                category_id=cat.id,
                content={"phrase": f"пара {{word}} {i}", "incorrect_answer": f"ошибка{i}"},
                answer=f"правильно{i}",
                explanation=f"Объяснение {i}",
            )
            exercises.append(ex)
        return cat, exercises

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "wrong_phrase_index": 0}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_7_EXAM)
        result = await processor.process_answer(dto, "правильно0")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "wrong_phrase_index": 0}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_7_EXAM)
        result = await processor.process_answer(dto, "ошибка")
        assert result.is_correct is False


# ===================================================================
# Task8 Exam — process_answer (9 exercises: 5 errors + 4 correct)
# ===================================================================

class TestTask8ExamProcessor:
    ERROR_TYPES = [
        "participial_clause_error", "homogeneous_members_error",
        "adverbial_participle_error", "prepositional_case_error",
        "subject_predicate_agreement",
    ]

    async def _make_exercises(self, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_8_EXAM)
        exercises = []
        for i, et in enumerate(self.ERROR_TYPES):
            ex = await exercise_factory(
                category_id=cat.id,
                content={"sentence": f"Ошибочное предложение {i}", "corrected_sentence": f"Исправленное {i}"},
                answer=et,
                explanation=f"Объяснение {i}",
            )
            exercises.append(ex)
        for i in range(4):
            ex = await exercise_factory(
                category_id=cat.id,
                content={"sentence": f"Правильное предложение {i}"},
                answer="no_error",
            )
            exercises.append(ex)
        return cat, exercises

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "error_type_order": self.ERROR_TYPES}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_8_EXAM)
        result = await processor.process_answer(dto, "12345")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "error_type_order": self.ERROR_TYPES}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_8_EXAM)
        result = await processor.process_answer(dto, "54321")
        assert result.is_correct is False


# ===================================================================
# Task9 Exam — process_answer (15 exercises: 5 rows × 3 words)
# ===================================================================

class TestTask9ExamProcessor:
    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_9_EXAM)
        exercises = []
        for i in range(15):
            ex = await exercise_factory(
                category_id=cat.id,
                content={"word": f"сл{{letter}}во{i}", "incorrect_letter": "е"},
                answer="и",
                explanation="Объяснение",
            )
            exercises.append(ex)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "correct_row_indices": [0, 2], "words_per_row": 3}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_9_EXAM)
        result = await processor.process_answer(dto, "13")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_9_EXAM)
        exercises = []
        for i in range(15):
            ex = await exercise_factory(
                category_id=cat.id,
                content={"word": f"сл{{letter}}во{i}", "incorrect_letter": "е"},
                answer="и",
                explanation="Объяснение",
            )
            exercises.append(ex)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "correct_row_indices": [0, 2], "words_per_row": 3}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_9_EXAM)
        result = await processor.process_answer(dto, "24")
        assert result.is_correct is False


# ===================================================================
# Task11 Exam — process_answer (10 exercises: 5 rows × 2 words)
# ===================================================================

class TestTask11ExamProcessor:
    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_11_EXAM)
        exercises = []
        for i in range(10):
            ex = await exercise_factory(
                category_id=cat.id,
                content={"word": f"сл{{letter}}во{i}", "incorrect_letter": "о"},
                answer="ё",
                explanation="Объяснение",
            )
            exercises.append(ex)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "correct_row_indices": [1, 3], "words_per_row": 2}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_11_EXAM)
        result = await processor.process_answer(dto, "24")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_11_EXAM)
        exercises = []
        for i in range(10):
            ex = await exercise_factory(
                category_id=cat.id,
                content={"word": f"сл{{letter}}во{i}", "incorrect_letter": "о"},
                answer="ё",
                explanation="Объяснение",
            )
            exercises.append(ex)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "correct_row_indices": [1, 3], "words_per_row": 2}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_11_EXAM)
        result = await processor.process_answer(dto, "15")
        assert result.is_correct is False


# ===================================================================
# Task13 Exam — process_answer (5 exercises)
# ===================================================================

class TestTask13ExamProcessor:
    async def _make_exercises(self, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_13_EXAM)
        answers = ["TOGETHER", "SEPARATE", "TOGETHER", "SEPARATE", "TOGETHER"]
        exercises = []
        for i, ans in enumerate(answers):
            ex = await exercise_factory(
                category_id=cat.id,
                content={"sentence": f"(НЕ)слово предложение {i}", "particle": "НЕ"},
                answer=ans,
                explanation=f"Объяснение {i}",
            )
            exercises.append(ex)
        return cat, exercises

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {
            "exercise_ids": exercise_ids,
            "correct_indices": [0, 2, 4],
            "answer_type": "TOGETHER",
            "mode": "НЕ",
        }
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_13_EXAM)
        result = await processor.process_answer(dto, "135")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {
            "exercise_ids": exercise_ids,
            "correct_indices": [0, 2, 4],
            "answer_type": "TOGETHER",
            "mode": "НЕ",
        }
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_13_EXAM)
        result = await processor.process_answer(dto, "24")
        assert result.is_correct is False


# ===================================================================
# Task14 Exam — process_answer (5 exercises)
# ===================================================================

class TestTask14ExamProcessor:
    async def _make_exercises(self, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_14_EXAM)
        answers = ["TOGETHER", "SEPARATE", "TOGETHER", "HYPHEN", "TOGETHER"]
        exercises = []
        for i, ans in enumerate(answers):
            ex = await exercise_factory(
                category_id=cat.id,
                content={
                    "sentence": f"Предложение {i} с выделенными словами",
                    "corrected_sentence": f"Предложение {i} исправленное",
                    "types": [ans],
                },
                answer=ans,
                explanation=f"Объяснение {i}",
            )
            exercises.append(ex)
        return cat, exercises

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {
            "exercise_ids": exercise_ids,
            "correct_indices": [0, 2, 4],
            "answer_type": "TOGETHER",
        }
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_14_EXAM)
        result = await processor.process_answer(dto, "135")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {
            "exercise_ids": exercise_ids,
            "correct_indices": [0, 2, 4],
            "answer_type": "TOGETHER",
        }
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_14_EXAM)
        result = await processor.process_answer(dto, "24")
        assert result.is_correct is False


# ===================================================================
# Task15 Exam — process_answer (1 exercise, answer with modes)
# ===================================================================

class TestTask15ExamProcessor:
    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_15_EXAM)
        ex = await exercise_factory(
            category_id=cat.id,
            content={
                "sentence": "Слово(1) и слово(2) и слово(3)",
                "corrected_sentence": "СловоН и словоНН и словоН",
                "modes": ["Н", "НН"],
            },
            answer="н;нн;н",
            explanation="Объяснение",
        )
        user = await user_factory()
        task_config = {"mode": "Н"}
        dto = _user_with_exercises(user, cat, [ex], task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_15_EXAM)
        result = await processor.process_answer(dto, "13")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_15_EXAM)
        ex = await exercise_factory(
            category_id=cat.id,
            content={
                "sentence": "Слово(1) и слово(2) и слово(3)",
                "corrected_sentence": "СловоН и словоНН и словоН",
                "modes": ["Н", "НН"],
            },
            answer="н;нн;н",
            explanation="Объяснение",
        )
        user = await user_factory()
        task_config = {"mode": "Н"}
        dto = _user_with_exercises(user, cat, [ex], task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_15_EXAM)
        result = await processor.process_answer(dto, "2")
        assert result.is_correct is False


# ===================================================================
# Task16 Exam — process_answer (5 exercises)
# ===================================================================

class TestTask16ExamProcessor:
    async def _make_exercises(self, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_16_EXAM)
        answers = ["1", "2", "1", "0", "1"]
        exercises = []
        for i, ans in enumerate(answers):
            ex = await exercise_factory(
                category_id=cat.id,
                content={
                    "sentence": f"Предложение без запятых {i}",
                    "corrected_sentence": f"Предложение, с запятыми {i}",
                },
                answer=ans,
                explanation=f"Объяснение {i}",
            )
            exercises.append(ex)
        return cat, exercises

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "correct_indices": [0, 2, 4]}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_16_EXAM)
        result = await processor.process_answer(dto, "135")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "correct_indices": [0, 2, 4]}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_16_EXAM)
        result = await processor.process_answer(dto, "24")
        assert result.is_correct is False


# ===================================================================
# Task22 Drill — create_task + process_answer
# ===================================================================

class TestTask22DrillProcessor:
    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P22", handler_type=HandlerType.TASK_22_DRILL)
        child = await category_factory(name="C22", handler_type=HandlerType.TASK_22_DRILL, parent_id=parent.id)
        await exercise_factory(
            category_id=parent.id,
            content={
                "sentence": "Метафоричное предложение",
                "distractor_devices": ["SIMILE", "EPITHET", "INVERSION", "ANAPHORA"],
                "other_devices": [],
                "excluded_devices": [],
            },
            answer="METAPHOR",
        )
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(HandlerType.TASK_22_DRILL)
        result = await processor.create_task(dto)
        assert result.task_ui.options is not None
        assert len(result.task_ui.options) == 5

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_22_DRILL)
        ex = await exercise_factory(
            category_id=cat.id,
            content={
                "sentence": "Метафоричное предложение",
                "distractor_devices": ["SIMILE", "EPITHET", "INVERSION", "ANAPHORA"],
                "other_devices": [],
                "excluded_devices": [],
            },
            answer="METAPHOR",
        )
        user = await user_factory()
        task_config = {"target": "METAPHOR"}
        dto = _user_with_exercises(user, cat, [ex], task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_22_DRILL)
        result = await processor.process_answer(dto, "METAPHOR")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_22_DRILL)
        ex = await exercise_factory(
            category_id=cat.id,
            content={
                "sentence": "Метафоричное предложение",
                "distractor_devices": ["SIMILE", "EPITHET", "INVERSION", "ANAPHORA"],
                "other_devices": [],
                "excluded_devices": [],
            },
            answer="METAPHOR",
        )
        user = await user_factory()
        task_config = {"target": "METAPHOR"}
        dto = _user_with_exercises(user, cat, [ex], task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_22_DRILL)
        result = await processor.process_answer(dto, "SIMILE")
        assert result.is_correct is False


# ===================================================================
# Task22 Exam — process_answer (5 exercises, 9 device options)
# ===================================================================

# ===================================================================
# Task15 Exam — create_task (single exercise with modes)
# ===================================================================

# ===================================================================
# Task7 Exam — create_task (5 exercises: 1 wrong + 4 filler)
# ===================================================================

class TestTask7ExamCreateTask:
    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P7e", handler_type=HandlerType.TASK_7_EXAM)
        child = await category_factory(name="C7e", handler_type=HandlerType.TASK_7_EXAM, parent_id=parent.id)
        await exercise_factory(
            category_id=parent.id,
            content={"phrase": "пара {word}", "incorrect_answer": "туфлей"},
            answer="туфель",
            explanation="Объяснение",
            group_id=uuid.uuid4(),
        )
        for i in range(4):
            await exercise_factory(
                category_id=parent.id,
                content={"phrase": f"фраза {{word}} {i}"},
                answer=f"слово{i}",
                explanation=f"Объяснение {i}",
                group_id=uuid.uuid4(),
            )
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(HandlerType.TASK_7_EXAM)
        result = await processor.create_task(dto)
        assert result.task_ui.view is not None
        assert result.task_config is not None
        assert len(result.exercise_ids) == 5


# ===================================================================
# Task8 Exam — create_task (9 exercises: 5 error + 4 no_error)
# ===================================================================

class TestTask8ExamCreateTask:
    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P8e", handler_type=HandlerType.TASK_8_EXAM)
        child = await category_factory(name="C8e", handler_type=HandlerType.TASK_8_EXAM, parent_id=parent.id)
        error_types = [
            "participial_clause_error", "homogeneous_members_error",
            "adverbial_participle_error", "prepositional_case_error",
            "subject_predicate_agreement",
        ]
        for i, et in enumerate(error_types):
            await exercise_factory(
                category_id=parent.id,
                content={"sentence": f"Ошибочное предложение {i}", "corrected_sentence": f"Исправленное {i}"},
                answer=et,
                explanation=f"Объяснение {i}",
            )
        for i in range(4):
            await exercise_factory(
                category_id=parent.id,
                content={"sentence": f"Правильное предложение {i}"},
                answer="no_error",
            )
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(HandlerType.TASK_8_EXAM)
        result = await processor.create_task(dto)
        assert result.task_ui.view is not None
        assert result.task_config is not None
        assert len(result.exercise_ids) == 9


class TestTask15ExamCreateTask:
    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_15_EXAM)
        await exercise_factory(
            category_id=cat.id,
            content={
                "sentence": "Серебря(1)ый кова(2)ый кубок",
                "corrected_sentence": "Серебряный кованый кубок",
                "modes": ["Н", "НН"],
            },
            answer="н;н",
            explanation="Объяснение",
        )
        user = await user_factory()
        dto = _user_dto(user, cat)

        processor = processor_factory.get_processor(HandlerType.TASK_15_EXAM)
        result = await processor.create_task(dto)
        assert result.task_ui.text is not None
        assert result.task_config is not None


# ===================================================================
# Task16 Exam — create_task (needs exercises with different answers)
# ===================================================================

class TestTask16ExamCreateTask:
    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P16e", handler_type=HandlerType.TASK_16_EXAM)
        child = await category_factory(name="C16e", handler_type=HandlerType.TASK_16_EXAM, parent_id=parent.id)
        for i in range(5):
            await exercise_factory(
                category_id=parent.id,
                content={"sentence": f"Предложение {i}", "corrected_sentence": f"Предложение, {i}"},
                answer="1",
                explanation=f"Объяснение {i}",
            )
        for i in range(5):
            await exercise_factory(
                category_id=parent.id,
                content={"sentence": f"Другое {i}", "corrected_sentence": f"Другое исправленное {i}"},
                answer="0",
                explanation=f"Объяснение {i}",
            )
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(HandlerType.TASK_16_EXAM)
        result = await processor.create_task(dto)
        assert result.task_ui.text is not None
        assert result.task_config is not None
        assert len(result.exercise_ids) == 5


# ===================================================================
# Task14 Exam — create_task (needs exercises with TOGETHER/SEPARATE/HYPHEN)
# ===================================================================

class TestTask14ExamCreateTask:
    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_14_EXAM)
        for i in range(5):
            await exercise_factory(
                category_id=cat.id,
                content={
                    "sentence": f"(ЧТО)БЫ предложение {i}",
                    "corrected_sentence": f"Чтобы предложение {i}",
                    "types": ["TOGETHER"],
                },
                answer="TOGETHER",
                explanation=f"Объяснение {i}",
            )
        for i in range(5):
            await exercise_factory(
                category_id=cat.id,
                content={
                    "sentence": f"(ПО)ЭТОМУ предложение {i}",
                    "corrected_sentence": f"По этому предложение {i}",
                    "types": ["SEPARATE"],
                },
                answer="SEPARATE",
                explanation=f"Объяснение {i}",
            )
        user = await user_factory()
        dto = _user_dto(user, cat)

        processor = processor_factory.get_processor(HandlerType.TASK_14_EXAM)
        result = await processor.create_task(dto)
        assert result.task_ui.view is not None
        assert result.task_config is not None
        assert len(result.exercise_ids) == 5


# ===================================================================
# Task13 Exam — create_task
# ===================================================================

class TestTask13ExamCreateTask:
    async def test_create_task(self, processor_factory, user_factory, category_factory, exercise_factory):
        parent = await category_factory(name="P13e", handler_type=HandlerType.TASK_13_EXAM)
        child = await category_factory(name="C13e", handler_type=HandlerType.TASK_13_EXAM, parent_id=parent.id)
        for i in range(5):
            await exercise_factory(
                category_id=parent.id,
                content={"sentence": f"(НЕ)слово слитно {i}", "particle": "НЕ"},
                answer="TOGETHER",
                explanation=f"Объяснение {i}",
            )
        for i in range(5):
            await exercise_factory(
                category_id=parent.id,
                content={"sentence": f"(НЕ)слово раздельно {i}", "particle": "НЕ"},
                answer="SEPARATE",
                explanation=f"Объяснение {i}",
            )
        for i in range(3):
            await exercise_factory(
                category_id=parent.id,
                content={"sentence": f"(НИ)слово слитно {i}", "particle": "НИ"},
                answer="TOGETHER",
                explanation=f"Объяснение НИ {i}",
            )
        for i in range(3):
            await exercise_factory(
                category_id=parent.id,
                content={"sentence": f"(НИ)слово раздельно {i}", "particle": "НИ"},
                answer="SEPARATE",
                explanation=f"Объяснение НИ {i}",
            )
        user = await user_factory()
        dto = _user_dto(user, child)

        processor = processor_factory.get_processor(HandlerType.TASK_13_EXAM)
        result = await processor.create_task(dto)
        assert result.task_ui.view is not None
        assert result.task_config is not None
        assert len(result.exercise_ids) == 5


# ===================================================================
# Task22 Exam — process_answer (5 exercises, 9 device options)
# ===================================================================

class TestTask22ExamProcessor:
    DEVICES = [
        "METAPHOR", "SIMILE", "EPITHET", "INVERSION", "ANAPHORA",
        "LITOTES", "HYPERBOLE", "GRADATION", "METONYMY",
    ]

    async def _make_exercises(self, category_factory, exercise_factory):
        cat = await category_factory(handler_type=HandlerType.TASK_22_EXAM)
        exercises = []
        for i in range(5):
            ex = await exercise_factory(
                category_id=cat.id,
                content={
                    "sentence": f"Предложение {i} с выразительным средством",
                    "distractor_devices": self.DEVICES[5:],
                    "other_devices": [],
                    "excluded_devices": [],
                },
                answer=self.DEVICES[i],
            )
            exercises.append(ex)
        return cat, exercises

    async def test_process_answer_correct(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "device_options": self.DEVICES}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_22_EXAM)
        result = await processor.process_answer(dto, "12345")
        assert result.is_correct is True

    async def test_process_answer_wrong(self, processor_factory, user_factory, category_factory, exercise_factory):
        cat, exercises = await self._make_exercises(category_factory, exercise_factory)
        user = await user_factory()
        exercise_ids = [ex.id for ex in exercises]
        task_config = {"exercise_ids": exercise_ids, "device_options": self.DEVICES}
        dto = _user_with_exercises(user, cat, exercises, task_config)

        processor = processor_factory.get_processor(HandlerType.TASK_22_EXAM)
        result = await processor.process_answer(dto, "98765")
        assert result.is_correct is False
